"""Pure functions that translate SearchFilters into OpenSearch query DSL.

No I/O, no side effects — fully unit-testable without mocking.

Query strategy:
  must  → multi_match on name (drives relevance score, fuzziness=AUTO)
          or match_all when no name is given
  filter → industry, locality, country, year range (bitset-cached, zero-score impact)
"""

from __future__ import annotations

from typing import Any, Optional

from company_search.domain.models import SearchFilters, SortField

_SORT_FIELD_MAP = {
    SortField.name: "name.keyword",
    SortField.size: "total_employee_estimate",
    SortField.founded_year: "year_founded",
}

_SOURCE_FIELDS = [
    "id",
    "name",
    "domain",
    "year_founded",
    "industry",
    "size_range",
    "locality",
    "country",
    "linkedin_url",
    "total_employee_estimate",
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
    body: dict[str, Any] = {
        "query": _build_query(filters),
        "from": (page - 1) * size,
        "size": size,
        "_source": _SOURCE_FIELDS,
        "track_total_hits": True,
    }
    if filters.sort_by:
        body["sort"] = [{_SORT_FIELD_MAP[filters.sort_by]: {"order": filters.sort_order.value, "missing": "_last"}}]
    return body


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


def _build_year_range(filters: SearchFilters) -> dict[str, int]:
    year_range: dict[str, int] = {}
    if filters.founded_year_min is not None:
        year_range["gte"] = filters.founded_year_min
    if filters.founded_year_max is not None:
        year_range["lte"] = filters.founded_year_max
    return year_range


def _build_term_clauses(filters: SearchFilters) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    if filters.industry:
        clauses.append({"term": {"industry.keyword": filters.industry}})
    if filters.locality:
        clauses.append({"match": {"locality": {"query": filters.locality, "fuzziness": "AUTO"}}})
    if filters.country:
        clauses.append({"term": {"country.keyword": filters.country}})
    if filters.size_range:
        clauses.append({"term": {"size_range": filters.size_range}})
    return clauses


def _build_filters(filters: SearchFilters) -> list[dict[str, Any]]:
    clauses = _build_term_clauses(filters)
    year_range = _build_year_range(filters)
    if year_range:
        clauses.append({"range": {"year_founded": year_range}})
    return clauses
