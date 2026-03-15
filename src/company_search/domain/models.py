"""Domain models — pure data structures, no external dependencies.

These are the canonical representations used across all layers.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SortField(str, Enum):
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
    sort_by: Optional[SortField] = None
    sort_order: SortOrder = SortOrder.asc


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
