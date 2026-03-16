"""Tag application service.

Phase 1: _normalize() is a simple slug (lowercase + hyphens).
Phase 3: swap _normalize() for an LLM call without changing callers.
"""

from __future__ import annotations

import re
from typing import Optional

from company_search.domain.tag_models import CompanyTagsResponse, Tag, TagCreate, TagSummary, TagType
from company_search.domain.tag_ports import TagRepository


def _normalize(tag: str) -> str:
    """Canonical tag form. Replace with LLM call in Phase 3."""
    return re.sub(r"[^a-z0-9]+", "-", tag.lower().strip()).strip("-")


class TagService:
    def __init__(self, repository: TagRepository) -> None:
        self._repo = repository

    def add_tag(self, company_id: str, tag_create: TagCreate) -> Tag:
        return self._repo.add_tag(
            company_id=company_id,
            tag=_normalize(tag_create.tag),
            tag_type=tag_create.tag_type,
            user_id=tag_create.user_id,
        )

    def remove_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> None:
        self._repo.remove_tag(company_id=company_id, tag=_normalize(tag), tag_type=tag_type, user_id=user_id)

    def list_tags(self, user_id: Optional[str]) -> list[TagSummary]:
        return self._repo.list_tags(user_id=user_id)

    def get_company_ids_for_tag(self, tag: str, user_id: Optional[str]) -> list[str]:
        return self._repo.get_company_ids_for_tag(tag=_normalize(tag), user_id=user_id)

    def list_tagged_companies(self, tag: str, user_id: Optional[str], page: int, size: int) -> CompanyTagsResponse:
        total, company_ids = self._repo.list_tagged_companies(
            tag=_normalize(tag), user_id=user_id, page=page, size=size
        )
        return CompanyTagsResponse(total=total, page=page, size=size, company_ids=company_ids)
