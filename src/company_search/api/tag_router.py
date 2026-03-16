"""Tags API router.

Company-centric tagging endpoints plus tag listing/browsing.
Public tags are visible to all; personal tags are scoped to a user_id.

Routes:
  POST   /companies/{company_id}/tags           Apply a tag to a company
  DELETE /companies/{company_id}/tags/{tag}     Remove a tag from a company
  GET    /tags                                  List tags (public + caller's personal)
  GET    /tags/{tag}/companies                  Companies carrying a specific tag
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from company_search.api.dependencies import get_tag_service
from company_search.application.tag_service import TagService
from company_search.domain.tag_models import CompanyTagsResponse, Tag, TagCreate, TagSummary, TagType

router = APIRouter(tags=["tags"])


@router.post("/companies/{company_id}/tags", response_model=Tag, status_code=201)
def apply_tag(
    company_id: str,
    body: TagCreate,
    service: Annotated[TagService, Depends(get_tag_service)],
) -> Tag:
    """Apply a tag to a company. Idempotent — applying the same tag twice has no effect.

    For personal tags, user_id must be provided in the request body.
    """
    if body.tag_type == TagType.personal and not body.user_id:
        raise HTTPException(status_code=422, detail="user_id is required for personal tags")
    return service.add_tag(company_id=company_id, tag_create=body)


@router.delete("/companies/{company_id}/tags/{tag}", status_code=204)
def remove_tag(
    company_id: str,
    tag: str,
    tag_type: Annotated[TagType, Query(description="Tag type: public or personal")],
    service: Annotated[TagService, Depends(get_tag_service)],
    user_id: Annotated[Optional[str], Query(description="User ID (required for personal tags)")] = None,
) -> None:
    """Remove a tag from a company."""
    if tag_type == TagType.personal and not user_id:
        raise HTTPException(status_code=422, detail="user_id is required for personal tags")
    service.remove_tag(company_id=company_id, tag=tag, tag_type=tag_type, user_id=user_id)


@router.get("/tags", response_model=list[TagSummary])
def list_tags(
    service: Annotated[TagService, Depends(get_tag_service)],
    user_id: Annotated[Optional[str], Query(description="User ID — includes personal tags when provided")] = None,
) -> list[TagSummary]:
    """List unique tags with company counts. Always includes public tags; personal tags require user_id."""
    return service.list_tags(user_id=user_id)


@router.get("/tags/{tag}/companies", response_model=CompanyTagsResponse)
def get_tagged_companies(
    tag: str,
    service: Annotated[TagService, Depends(get_tag_service)],
    user_id: Annotated[Optional[str], Query(description="User ID — includes personal tags when provided")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 10,
) -> CompanyTagsResponse:
    """List company IDs carrying a specific tag, paginated."""
    return service.list_tagged_companies(tag=tag, user_id=user_id, page=page, size=size)
