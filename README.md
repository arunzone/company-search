# Company Search — Technical Documentation

---

## Project Overview

A production-grade company search API over the 7M dataset. The system supports structured filtering (industry, location, founding year, size), relevance-ranked full-text search, and intelligent query understanding via synonym expansion — with a tagging system for personal/shared company organisation.

---

## Architecture Overview

```
HTTP Request
    ↓
[FastAPI Router]          ← validates params, maps to domain models
    ↓
[SearchService]           ← orchestrates tag resolution, thin layer
    ↓
[QueryBuilder]            ← pure functions, builds OpenSearch DSL
    ↓
[OpenSearchRepository]    ← executes query, maps hits → domain models
    ↓
[OpenSearch 3-shard]      ← full-text search, bitset filter cache, scoring
```

**Key components:**
- **API Layer** — FastAPI routers for search, tags, health, and Prometheus metrics
- **Domain Layer** — `SearchFilters`, `SearchResult`, `Tag` models; `QueryBuilder` pure functions; repository `Protocol` interfaces
- **Application Layer** — `SearchService` (search + tag orchestration), `TagService` (normalisation)
- **Infrastructure Layer** — OpenSearch client, `SearchRepository` and `TagRepository` implementations
- **Observability** — Structured JSON logging middleware, OpenTelemetry traces, Prometheus `/metrics`

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hexagonal architecture** | Domain logic has zero infrastructure imports. Swapping OpenSearch for Elasticsearch or a stub requires changing one file. Tests run without a live cluster. |
| **`Protocol`-based ports** | `SearchRepository` and `TagRepository` are structural interfaces — no base classes, no inheritance. Enables lightweight test doubles via duck typing. |
| **`QueryBuilder` as pure functions** | All DSL construction is stateless and I/O-free. 100% unit testable without containers or mocks. |
| **Synonym expansion at index time** | Industry synonyms (`tech → information technology and services`) are baked in via a custom analyser. Query time stays simple; relevance stays consistent. |
| **Separate `name_index` vs `name_search` analyser** | Edge n-gram on index-time enables prefix search; standard tokeniser on search-time avoids score dilution from n-gram matching at query time. |
| **Filter vs must clauses** | All non-text filters (country, year range, size) go in `bool.filter` — they use OpenSearch's bitset cache and don't affect BM25 scoring. |
| **Idempotent tag documents** | Tag doc ID is `{type}|{user_id}|{company_id}|{tag}`. Re-applying the same tag is a no-op upsert — no duplicate handling needed in application code. |

---

## Implementation Highlights

**OpenSearch index design:**
- 3 shards (~2.3M docs/shard), 1 replica — sized for 60 RPS with headroom for replica-fan-out reads
- `industry` field carries synonym filter: `software → computer software`, `healthcare → hospital & health care`, enabling semantic matching without an LLM at query time
- `name` field has `edge_ngram` (min 2, max 20) — prefix search works from the second character

**Query construction (`query_builder.py`):**
- `name` → `multi_match` on `["name^3", "domain"]` with `fuzziness: AUTO, prefix_length: 1` — typo-tolerant, name-boosted
- Filters → `bool.filter[]` bitset-cached, zero scoring cost
- `company_ids` filter enables tag-scoped search: service resolves tag → company ID list, appended as `ids` filter clause

**Tag system (`tag_service.py`, `tag_repository.py`):**
- Two visibility levels: `public` (all users) and `personal` (user-scoped)
- `list_tags(user_id)` returns union of public tags + user's personal tags
- Normalisation (`"Tech Leaders!" → "tech-leaders"`) is intentionally isolated as a single method — the Phase 3 swap point for LLM-based canonicalisation

**Data pipeline (`scripts/index_companies.py`):**
- Reads 7M-row CSV in 5,000-row chunks (memory-safe)
- Bulk-indexes in 500-doc batches with 4 worker threads — ~15–30 min total
- `clean_row` handles CSV data quality: float years → int, empty strings → `null`, field name remapping

**Observability:**
- `RequestLoggingMiddleware` emits structured JSON per request: method, path, status, `latency_ms`
- OpenTelemetry auto-instruments all FastAPI routes; `GET /metrics` exposes Prometheus histograms
- `GET /health` returns OpenSearch cluster colour — ready for load-balancer health checks

---

## Engineering Best Practices

- **Separation of concerns** — routing, orchestration, query building, and I/O are in distinct layers with no cross-cutting imports
- **SOLID** — `SearchRepository` Protocol satisfies ISP; `QueryBuilder` is open for extension (new filter clauses) without touching existing logic; `SearchService` depends on abstractions not implementations
- **KISS** — `QueryBuilder` is a module of pure functions, not a class hierarchy. No abstraction until warranted
- **Quality gate enforced via tox** — `ruff` (lint + format), `mypy` (type checking), `bandit` (security), `radon`/`xenon` (complexity), `pytest --cov=80` all run in CI before merge
- **Configuration as code** — `pydantic-settings` validates all env vars at startup; no `os.environ.get()` scattered through the codebase

---

## Scalability and Performance

| Concern | Approach |
|---------|----------|
| **60 RPS search** | 3-shard index; connection pool of 25; `bool.filter` bitset cache eliminates re-scoring on repeated filter combinations |
| **60 RPS simultaneous filter** | Stateless API (no shared mutable state); async FastAPI; OpenSearch shard-level parallelism |
| **Tag-scoped search at scale** | Tag resolution returns a flat list of IDs; `ids` filter is O(1) per doc in OpenSearch's bitset engine |
| **LLM path at 30 RPS** | Tag normalisation is isolated as a single function call — wrapping it in an async LLM call with a local cache (`lru_cache` or Redis) requires no other changes |
| **Horizontal scaling** | API is fully stateless — any number of replicas behind a load balancer. OpenSearch scales via replica shards for read-heavy workloads |

---

## Future Improvements

1. **Query-time synonym expansion via embeddings** — Replace static synonym file with dense vector nearest-neighbour on the `industry` field for more robust semantic matching
2. **Caching layer** — Redis in front of OpenSearch for repeated identical queries (high value for autocomplete and popular filters)
3. **Async I/O throughout** — Switch `OpenSearch` client to `AsyncOpenSearch` to remove blocking I/O from the event loop under high concurrency
4. **Tag consistency via LLM canonicalisation** — Replace the regex `_normalize()` with an LLM call that clusters semantically equivalent tags (`"competitors"`, `"competition"`, `"rival companies"`) into a canonical form

---

## Setup

### Prerequisites
- Docker and Docker Compose
- The [Kaggle 7M Companies dataset](https://www.kaggle.com/datasets/peopledatalabssf/free-7-million-company-dataset) CSV placed at `data/companies_sorted.csv`

### Run the full stack

```bash
docker compose up
```

This starts OpenSearch, runs the indexing pipeline (~15–30 min for 7M docs), then starts the API on port `8000`.

### Development (OpenSearch only)

```bash
docker compose -f docker-compose.dev.yml up
```

### Re-index from scratch

```bash
docker-compose run --rm setup python scripts/index_companies.py --recreate
```

### Run tests

```bash
docker-compose -f docker-compose.dev.yml run --rm app tox
```

---

## API Reference

### Search

```
GET /companies/search
```

| Param | Type | Description |
|-------|------|-------------|
| `name` | string | Company name (fuzzy, prefix-aware) |
| `industry` | string | Exact industry filter (synonym-expanded) |
| `locality` | string | City/locality (partial match) |
| `country` | string | Country (exact) |
| `founded_year_min` | int | Founding year range start |
| `founded_year_max` | int | Founding year range end |
| `size_range` | string | e.g. `10001+`, `1001-5000` |
| `tags` | `public` \| `personal` | Filter to tagged companies |
| `sort_by` | `relevance` \| `name` \| `size` \| `founded_year` | Sort field |
| `sort_order` | `asc` \| `desc` | Sort direction |
| `user_id` | string | Includes personal tags for this user |
| `page` | int | Page number (default: 1) |
| `size` | int | Results per page (default: 10, max: 100) |

### Tags

```
POST   /companies/{company_id}/tags
DELETE /companies/{company_id}/tags/{tag}?tag_type=X&user_id=Y
GET    /tags?user_id=Y
GET    /tags/{tag}/companies?user_id=Y&page=1&size=10
```

### Observability

```
GET /health    → OpenSearch cluster status
GET /metrics   → Prometheus metrics
```
