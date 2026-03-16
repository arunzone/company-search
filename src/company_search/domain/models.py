"""Domain models — pure data structures, no external dependencies.

These are the canonical representations used across all layers.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, model_validator

from company_search.domain.tag_models import TagType


class SortField(str, Enum):
    relevance = "relevance"
    name = "name"
    size = "size"
    founded_year = "founded_year"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class SearchFilters(BaseModel):
    """Structured search parameters. Decoupled from HTTP concerns."""

    name: Optional[str] = None
    industry: Optional[str] = None
    locality: Optional[str] = None
    country: Optional[str] = None
    founded_year_min: Optional[int] = None
    founded_year_max: Optional[int] = None
    size_range: Optional[str] = None
    tags: Optional[list[TagType]] = []
    user_id: Optional[str] = None
    company_ids: Optional[list[str]] = None
    sort_by: Optional[SortField] = None
    sort_order: SortOrder = SortOrder.asc
    page: int = 1
    size: int = 10

    @model_validator(mode="after")
    def _check_year_range(self) -> "SearchRequest":
        if self.founded_year_min and self.founded_year_max:
            if self.founded_year_min > self.founded_year_max:
                raise ValueError("founded_year_min must be <= founded_year_max")
        return self


class SearchRequest(BaseModel):
    """POST body for /companies/search.

    tags + user_id are resolved to company IDs before querying OpenSearch.
    Public tags are matched for all users; personal tags require user_id.
    """

    name: Optional[str] = None
    industry: Optional[str] = None
    locality: Optional[str] = None
    country: Optional[str] = None
    founded_year_min: Optional[int] = None
    founded_year_max: Optional[int] = None
    size_range: Optional[str] = None
    tags: Optional[list[TagType]] = None
    user_id: Optional[str] = None
    sort_by: Optional[SortField] = None
    sort_order: SortOrder = SortOrder.asc
    page: int = 1
    size: int = 10

    @model_validator(mode="after")
    def _check_year_range(self) -> "SearchRequest":
        if self.founded_year_min and self.founded_year_max:
            if self.founded_year_min > self.founded_year_max:
                raise ValueError("founded_year_min must be <= founded_year_max")
        return self


class SearchResult(BaseModel):
    """A single search hit with relevance score."""

    id: str
    name: str
    domain: Optional[str] = None
    year_founded: Optional[int] = None
    industry: Optional[str] = None
    size_range: Optional[str] = None
    locality: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    total_employee_estimate: Optional[int] = None
    score: float = 0.0


class SearchResponse(BaseModel):
    """Paginated search response returned to the caller."""

    total: int
    page: int
    size: int
    results: list[SearchResult]
