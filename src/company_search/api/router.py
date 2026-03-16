"""Company search API router.

Single endpoint: GET /companies/search
All HTTP-specific concerns (param parsing, error responses) live here.
Business logic lives in SearchService; query building in query_builder.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from company_search.domain.tag_models import TagType
from fastapi import APIRouter, Depends, HTTPException, Query

from company_search.api.dependencies import get_search_service
from company_search.application.search_service import SearchService
from company_search.domain.models import SearchFilters, SearchResponse, SortField, SortOrder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


def _validate_year_range(min_year: Optional[int], max_year: Optional[int]) -> None:
    if min_year and max_year and min_year > max_year:
        raise HTTPException(status_code=422, detail="founded_year_min must be <= founded_year_max")


@router.get("/search", response_model=SearchResponse)
def search_companies(
    name: Annotated[Optional[str], Query(description="Company name (fuzzy match)")] = None,
    industry: Annotated[Optional[str], Query(description="Exact industry filter")] = None,
    locality: Annotated[Optional[str], Query(description="City/locality (fuzzy match)")] = None,
    country: Annotated[Optional[str], Query(description="Country (exact match)")] = None,
    founded_year_min: Annotated[Optional[int], Query(description="Founded year range start", ge=1800, le=2100)] = None,
    founded_year_max: Annotated[Optional[int], Query(description="Founded year range end", ge=1800, le=2100)] = None,
    size_range: Annotated[Optional[str], Query(description="Size range exact match, e.g. '10001+'")] = None,
    tags: Annotated[Optional[list[TagType]], Query(description="Filter by tag")] = None,
    sort_by: Annotated[
        Optional[SortField], Query(description="Sort field: relevance, name, size, founded_year")
    ] = None,
    sort_order: Annotated[SortOrder, Query(description="Sort order: asc or desc")] = SortOrder.asc,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 10,
    user_id: Annotated[Optional[str], Query(description="User ID — includes personal tags when provided")] = None,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Search companies by name, industry, locality, country, and founding year.

    Pass user_id= to scope results to that user's tagged companies.
    """
    _validate_year_range(founded_year_min, founded_year_max)

    filters = SearchFilters(
        name=name,
        industry=industry,
        locality=locality,
        country=country,
        founded_year_min=founded_year_min,
        founded_year_max=founded_year_max,
        size_range=size_range,
        tags=tags or [],
        user_id=user_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    try:
        return service.search(filters=filters, page=page, size=size)
    except RuntimeError as exc:
        logger.exception("Search request failed")
        raise HTTPException(status_code=503, detail="Search service unavailable") from exc
