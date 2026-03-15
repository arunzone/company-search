"""Domain models — pure data structures, no external dependencies.

These are the canonical representations used across all layers.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Structured search parameters. Decoupled from HTTP concerns."""

    name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    founded_year_min: Optional[int] = None
    founded_year_max: Optional[int] = None
    size_range: Optional[str] = None


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
    score: float = 0.0


class SearchResponse(BaseModel):
    """Paginated search response returned to the caller."""

    total: int
    page: int
    size: int
    results: list[SearchResult]
