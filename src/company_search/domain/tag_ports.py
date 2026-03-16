"""Tag domain ports — contracts for tag persistence."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from company_search.domain.tag_models import Tag, TagSummary, TagType


@runtime_checkable
class TagRepository(Protocol):
    """Contract for persisting and retrieving company tags (public and personal)."""

    def add_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> Tag: ...

    def remove_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> None: ...

    def list_tags(self, user_id: Optional[str]) -> list[TagSummary]: ...

    def get_company_ids_for_tag(self, tag: str, user_id: Optional[str]) -> list[str]: ...

    def list_tagged_companies(
        self, tag: str, user_id: Optional[str], page: int, size: int
    ) -> tuple[int, list[str]]: ...
