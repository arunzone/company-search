"""Pure functions that translate SearchFilters into OpenSearch query DSL.

No I/O, no side effects — fully unit-testable without mocking.

Query strategy:
  must  → multi_match on name (drives relevance score, fuzziness=AUTO)
          or match_all when no name is given
  filter → industry, location, year range (bitset-cached, zero-score impact)
"""

from __future__ import annotations

from typing import Any, Optional

from company_search.domain.models import SearchFilters

_SOURCE_FIELDS = [
    "id", "name", "domain", "year_founded", "industry",
    "size_range", "locality", "country", "linkedin_url",
]


def build_search_body(filters: SearchFilters, page: int, size: int) -> dict[str, Any]:
    """Assemble the complete OpenSearch request body.

    Args:
        filters: Structured search parameters.
        page: 1-based page number.
        size: Results per page.

    Returns:
        Full OpenSearch search request body.
    """
    return {
        "query": _build_query(filters),
        "from": (page - 1) * size,
        "size": size,
        "_source": _SOURCE_FIELDS,
        "track_total_hits": True,
    }


def _build_query(filters: SearchFilters) -> dict[str, Any]:
    return {
        "bool": {
            "must": _build_must(filters.name),
            "filter": _build_filters(filters),
        }
    }


def _build_must(name: Optional[str]) -> list[dict[str, Any]]:
    if not name:
        return [{"match_all": {}}]
    return [
        {
            "multi_match": {
                "query": name,
                "fields": ["name^3", "domain"],
                "type": "best_fields",
                "fuzziness": "AUTO",
                "prefix_length": 1,
            }
        }
    ]


def _build_filters(filters: SearchFilters) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []

    if filters.industry:
        clauses.append({"term": {"industry.keyword": filters.industry}})

    if filters.location:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"match": {"locality": {"query": filters.location, "fuzziness": "AUTO"}}},
                        {"match": {"country": {"query": filters.location, "fuzziness": "AUTO"}}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    year_range: dict[str, int] = {}
    if filters.founded_year_min is not None:
        year_range["gte"] = filters.founded_year_min
    if filters.founded_year_max is not None:
        year_range["lte"] = filters.founded_year_max
    if year_range:
        clauses.append({"range": {"year_founded": year_range}})

    if filters.size_range:
        clauses.append({"term": {"size_range": filters.size_range}})

    return clauses
