# Company Search API

A production-grade company search API built with **FastAPI** and **OpenSearch**, backed by the [7 Million Company Dataset](https://www.kaggle.com/datasets/peopledatalabssf/free-7-million-company-dataset).

Search 7M companies by name, industry, location, and founding year — with fuzzy matching, relevance scoring, and full pagination.

---

## Architecture

```
GET /companies/search
        │
   [API Router]              validates HTTP params, returns HTTP errors
        │ SearchFilters
   [SearchService]           thin orchestrator (seam for future NL layer)
        │
   [QueryBuilder]            pure functions: filters → OpenSearch DSL
        │
   [OpenSearchRepository]    executes query, maps hits → domain models
        │
   [OpenSearch]              3-shard index, synonym analysis, edge n-grams
```

**Layer responsibilities:**

| Layer | Location | Responsibility |
|---|---|---|
| API | `api/router.py` | HTTP params, validation, error codes |
| Application | `application/search_service.py` | Orchestration only |
| Domain | `domain/` | Models, ports (interfaces), pure query builder |
| Infrastructure | `infrastructure/opensearch/` | OpenSearch client, repository, index mapping |
| Observability | `observability/logging.py` | Structured JSON logging, request middleware |

---

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (for local development)
- The dataset CSV at `data/companies_sorted.csv`

---

## Quick Start (Docker)

### Example Usage

  #### Start stack
  docker-compose up

  #### Index data (run once)
  docker-compose exec app python scripts/index_companies.py --recreate

  #### Search by name
  GET /companies/search?name=ibm

  #### Filtered: tech companies in US founded after 2000
  GET /companies/search?industry=information+technology+and+services&location=united+states&founded_year_m
  in=2000

  #### Paginated
  GET /companies/search?name=accenture&page=2&size=20

  #### Performance test
  `ab -n 60 -c 60 "http://127.0.0.1:8000/companies/search?name=ibm"`


### 1. Start OpenSearch + index data + run API

```bash
docker-compose up
```

This runs three steps in order:
1. `opensearch` — starts OpenSearch (waits until healthy)
2. `setup` — creates the index and bulk-indexes the CSV
3. `app` — starts the FastAPI server on port `8000`

OpenSearch Dashboards is available at [http://localhost:5601](http://localhost:5601).

> **First run note:** Indexing 7M documents takes ~15–30 minutes depending on your machine. Progress is logged to the `setup` container.

### 2. Test the API

```bash
curl "http://localhost:8000/companies/search?name=ibm"
```

---

## Development Setup

### 1. Start OpenSearch only

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Install the package in editable mode

```bash
pip install -e ".[testing]"
```

### 3. Set environment variables

```bash
cp .env.example .env
# Edit .env if your OpenSearch config differs from defaults
```

### 4. Run the API locally

```bash
python -m company_search
```

API is available at [http://localhost:8000](http://localhost:8000).
Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Indexing Data

Run the indexing script to load the CSV into OpenSearch:

```bash
# Default: index to existing index (skips if index exists)
python scripts/index_companies.py

# Force recreate the index and re-index all data
python scripts/index_companies.py --recreate

# Custom CSV path
python scripts/index_companies.py --csv /path/to/companies.csv --recreate
```

**What the script does:**
- Reads the CSV in 5 000-row chunks (memory-safe for 7M rows)
- Cleans data: `NaN → None`, `float years → int`
- Skips rows with no company name
- Bulk-indexes in parallel batches of 500 documents
- Reports progress and error counts

---

## API Reference

### `GET /companies/search`

Search companies with optional filters.

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Company name — fuzzy match with relevance scoring |
| `industry` | string | Exact industry filter (e.g. `computer software`) |
| `location` | string | Locality or country — partial match |
| `founded_year_min` | integer | Founding year range start (inclusive) |
| `founded_year_max` | integer | Founding year range end (inclusive) |
| `size_range` | string | Exact size range (e.g. `10001+`, `51-200`) |
| `page` | integer | Page number, default `1` |
| `size` | integer | Results per page, default `10`, max `100` |

**Response:**

```json
{
  "total": 42381,
  "page": 1,
  "size": 10,
  "results": [
    {
      "id": "5872184",
      "name": "ibm",
      "domain": "ibm.com",
      "year_founded": 1911,
      "industry": "information technology and services",
      "size_range": "10001+",
      "locality": "new york, new york, united states",
      "country": "united states",
      "linkedin_url": "linkedin.com/company/ibm",
      "score": 12.34
    }
  ]
}
```

**Example queries:**

```bash
# Search by name (fuzzy)
curl "http://localhost:8000/companies/search?name=ibm"

# Filter by industry
curl "http://localhost:8000/companies/search?industry=computer+software"

# Filter by location
curl "http://localhost:8000/companies/search?location=california"

# Year range filter
curl "http://localhost:8000/companies/search?founded_year_min=2000&founded_year_max=2010"

# Combined filters
curl "http://localhost:8000/companies/search?industry=internet&location=united+states&founded_year_min=2005&size_range=51-200"

# Pagination
curl "http://localhost:8000/companies/search?name=accenture&page=2&size=20"
```

**Known industry values:**

```
information technology and services
computer software
internet
financial services
hospital & health care
management consulting
marketing and advertising
real estate
pharmaceuticals
telecommunications
mechanical or industrial engineering
logistics and supply chain
```

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov company_search --cov-report term-missing

# Run full quality gate (lint + type check + security + tests)
tox

# Format code
tox -e format

# Tests only (no linting)
tox -e test
```

**Test strategy:**
- `tests/test_query_builder.py` — pure unit tests, no mocking, no OpenSearch required
- `tests/test_search_endpoint.py` — API tests using a stub repository (no OpenSearch required)

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENSEARCH_HOST` | `localhost` | OpenSearch hostname |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `OPENSEARCH_USER` | `admin` | OpenSearch username |
| `OPENSEARCH_PASSWORD` | `OpenSearch!C0mp@ny` | OpenSearch password |
| `OPENSEARCH_USE_SSL` | `true` | Enable SSL |
| `OPENSEARCH_VERIFY_CERTS` | `false` | Verify SSL certs |
| `OPENSEARCH_INDEX` | `companies` | Index name |
| `FASTAPI_HOST` | `0.0.0.0` | API bind host |
| `FASTAPI_PORT` | `8000` | API bind port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`) |

---

## Index Design

**3 shards** — sized for 7M documents (~2.3M/shard), supports 60 RPS with pool size of 25 connections.

**Field mapping highlights:**

| Field | Type | Notes |
|---|---|---|
| `name` | `text` + `.keyword` | Edge n-gram at index time for prefix search; standard analyzer at search time |
| `industry` | `text` + `.keyword` | Synonym filter maps `"tech"` → `"information technology and services"` at index time |
| `locality` / `country` | `text` + `.keyword` | Partial match + fuzzy for location search |
| `year_founded` | `integer` | Range queries |
| `size_range` | `keyword` | Exact filter |

**Industry synonym examples** (mapped at index time, no runtime cost):

```
tech, technology → information technology and services
software         → computer software
healthcare       → hospital & health care
ecommerce        → internet
consulting       → management consulting
```

---

## Observability

All logs are emitted as **structured JSON** to stdout, suitable for Datadog, CloudWatch, or any log aggregator.

**Per-request log** (from middleware):
```json
{"ts": "2026-03-15T10:00:00", "level": "INFO", "logger": "company_search.access",
 "msg": "{\"method\": \"GET\", \"path\": \"/companies/search\", \"query\": \"name=ibm\", \"status\": 200, \"latency_ms\": 23.4}"}
```

**Search log** (from service):
```json
{"ts": "2026-03-15T10:00:00", "level": "INFO", "logger": "company_search.application.search_service",
 "msg": "search filters={'name': 'ibm'} page=1 size=10"}
```

Set `LOG_LEVEL=DEBUG` to see the full OpenSearch query body per request.

---

## Project Structure

```
company-search/
├── data/
│   └── companies_sorted.csv          7M company dataset
├── scripts/
│   └── index_companies.py            Bulk indexing script
├── src/company_search/
│   ├── domain/
│   │   ├── models.py                 SearchFilters, SearchResult, SearchResponse
│   │   ├── ports.py                  SearchRepository Protocol
│   │   └── query_builder.py          Pure OpenSearch DSL builder
│   ├── application/
│   │   └── search_service.py         Orchestration
│   ├── infrastructure/opensearch/
│   │   ├── client.py                 Connection factory
│   │   ├── index_mapping.py          Index settings + analyzers
│   │   └── repository.py             SearchRepository implementation
│   ├── api/
│   │   ├── router.py                 GET /companies/search
│   │   └── dependencies.py           FastAPI DI wiring
│   ├── observability/
│   │   └── logging.py                JSON logger + request middleware
│   ├── config.py
│   ├── main.py
│   └── __main__.py
├── tests/
│   ├── test_query_builder.py
│   └── test_search_endpoint.py
├── docker-compose.yml                Full stack (OpenSearch + API)
├── docker-compose.dev.yml            Dev (OpenSearch only)
├── Dockerfile.dev
├── pyproject.toml
├── setup.cfg
└── tox.ini
```
