"""Unit tests for TagService — no I/O, stub repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from company_search.application.tag_service import TagService, _normalize
from company_search.domain.tag_models import CompanyTagsResponse, Tag, TagCreate, TagSummary, TagType


# ---------------------------------------------------------------------------
# Stub repository
# ---------------------------------------------------------------------------


class StubTagRepository:
    def __init__(self) -> None:
        self._docs: dict[str, Tag] = {}

    def _key(self, tag_type: TagType, user_id: Optional[str], company_id: str, tag: str) -> str:
        return f"{tag_type.value}|{user_id or 'public'}|{company_id}|{tag}"

    def add_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> Tag:
        t = Tag(
            user_id=user_id,
            company_id=company_id,
            tag=tag,
            tag_type=tag_type,
            created_at=datetime.now(timezone.utc),
        )
        self._docs[self._key(tag_type, user_id, company_id, tag)] = t
        return t

    def remove_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> None:
        self._docs.pop(self._key(tag_type, user_id, company_id, tag), None)

    def _is_visible(self, t: Tag, user_id: Optional[str]) -> bool:
        if t.tag_type == TagType.public:
            return True
        return bool(user_id and t.tag_type == TagType.personal and t.user_id == user_id)

    def list_tags(self, user_id: Optional[str]) -> list[TagSummary]:
        relevant = [t for t in self._docs.values() if self._is_visible(t, user_id)]
        ids_map: dict[tuple[str, TagType], list[str]] = {}
        for t in relevant:
            ids_map.setdefault((t.tag, t.tag_type), []).append(t.company_id)
        return [TagSummary(tag=tag, tag_type=tt, company_ids=ids) for (tag, tt), ids in ids_map.items()]

    def get_company_ids_for_tag(self, tag: str, user_id: Optional[str]) -> list[str]:
        return [t.company_id for t in self._docs.values() if t.tag == tag and self._is_visible(t, user_id)]

    def list_tagged_companies(self, tag: str, user_id: Optional[str], page: int, size: int) -> tuple[int, list[str]]:
        ids = self.get_company_ids_for_tag(tag, user_id)
        offset = (page - 1) * size
        return len(ids), ids[offset : offset + size]


@pytest.fixture()
def repo() -> StubTagRepository:
    return StubTagRepository()


@pytest.fixture()
def service(repo: StubTagRepository) -> TagService:
    return TagService(repository=repo)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercases(self) -> None:
        assert _normalize("COMPETITORS") == "competitors"

    def test_replaces_spaces_with_hyphens(self) -> None:
        assert _normalize("tech startups") == "tech-startups"

    def test_strips_special_chars(self) -> None:
        assert _normalize("fin-tech!") == "fin-tech"

    def test_collapses_multiple_separators(self) -> None:
        assert _normalize("a  --  b") == "a-b"


# ---------------------------------------------------------------------------
# TagService
# ---------------------------------------------------------------------------


class TestAddTag:
    def test_normalizes_before_storing(self, service: TagService, repo: StubTagRepository) -> None:
        service.add_tag(
            "c1",
            TagCreate(tag="Tech Startups", tag_type=TagType.personal, user_id="u1"),
        )
        ids = repo.get_company_ids_for_tag("tech-startups", "u1")
        assert "c1" in ids

    def test_returns_tag(self, service: TagService) -> None:
        tag = service.add_tag("c1", TagCreate(tag="competitors", tag_type=TagType.personal, user_id="u1"))
        assert isinstance(tag, Tag)
        assert tag.tag == "competitors"

    def test_idempotent(self, service: TagService, repo: StubTagRepository) -> None:
        tc = TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1")
        service.add_tag("c1", tc)
        service.add_tag("c1", tc)
        assert repo.get_company_ids_for_tag("targets", "u1").count("c1") == 1

    def test_public_tag_no_user_id(self, service: TagService) -> None:
        tag = service.add_tag("c1", TagCreate(tag="hot-prospect", tag_type=TagType.public))
        assert tag.tag_type == TagType.public
        assert tag.user_id is None


class TestRemoveTag:
    def test_removes_personal_tag(self, service: TagService, repo: StubTagRepository) -> None:
        service.add_tag("c1", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1"))
        service.remove_tag("c1", "targets", TagType.personal, "u1")
        assert repo.get_company_ids_for_tag("targets", "u1") == []

    def test_normalizes_before_removing(self, service: TagService, repo: StubTagRepository) -> None:
        service.add_tag("c1", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1"))
        service.remove_tag("c1", "TARGETS", TagType.personal, "u1")
        assert repo.get_company_ids_for_tag("targets", "u1") == []


class TestListTags:
    def test_returns_personal_tags_for_user(self, service: TagService) -> None:
        service.add_tag("c1", TagCreate(tag="competitors", tag_type=TagType.personal, user_id="u1"))
        service.add_tag("c2", TagCreate(tag="competitors", tag_type=TagType.personal, user_id="u1"))
        service.add_tag("c3", TagCreate(tag="partners", tag_type=TagType.personal, user_id="u1"))
        summaries = service.list_tags("u1")
        counts = {s.tag: len(s.company_ids) for s in summaries}
        assert counts["competitors"] == 2
        assert counts["partners"] == 1

    def test_includes_public_tags(self, service: TagService) -> None:
        service.add_tag("c1", TagCreate(tag="hot-prospect", tag_type=TagType.public))
        summaries = service.list_tags(None)
        assert any(s.tag == "hot-prospect" and s.tag_type == TagType.public for s in summaries)

    def test_isolates_personal_tags_per_user(self, service: TagService) -> None:
        service.add_tag("c1", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1"))
        service.add_tag("c2", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u2"))
        assert len(service.list_tags("u1")) == 1


class TestGetCompanyIdsForTag:
    def test_returns_matching_personal_company_ids(self, service: TagService) -> None:
        service.add_tag("c1", TagCreate(tag="prospects", tag_type=TagType.personal, user_id="u1"))
        service.add_tag("c2", TagCreate(tag="prospects", tag_type=TagType.personal, user_id="u1"))
        ids = service.get_company_ids_for_tag("prospects", "u1")
        assert set(ids) == {"c1", "c2"}

    def test_returns_public_tag_companies_without_user(self, service: TagService) -> None:
        service.add_tag("c1", TagCreate(tag="hot-prospect", tag_type=TagType.public))
        ids = service.get_company_ids_for_tag("hot-prospect", None)
        assert "c1" in ids

    def test_returns_empty_for_unknown_tag(self, service: TagService) -> None:
        assert service.get_company_ids_for_tag("nonexistent", "u1") == []


class TestListTaggedCompanies:
    def test_returns_paginated_response(self, service: TagService) -> None:
        for i in range(5):
            service.add_tag(f"c{i}", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1"))
        result = service.list_tagged_companies("targets", "u1", page=1, size=3)
        assert isinstance(result, CompanyTagsResponse)
        assert result.total == 5
        assert len(result.company_ids) == 3

    def test_second_page(self, service: TagService) -> None:
        for i in range(5):
            service.add_tag(f"c{i}", TagCreate(tag="targets", tag_type=TagType.personal, user_id="u1"))
        result = service.list_tagged_companies("targets", "u1", page=2, size=3)
        assert len(result.company_ids) == 2
