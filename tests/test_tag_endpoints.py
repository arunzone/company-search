"""Integration-style tests for the tags API — stub repository, no OpenSearch required."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from company_search.api.dependencies import get_tag_service
from company_search.application.tag_service import TagService
from company_search.domain.tag_models import Tag, TagSummary, TagType
from company_search.main import app

USER_ID = "user-123"


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
        counts: Counter[tuple[str, TagType]] = Counter((t.tag, t.tag_type) for t in relevant)
        return [TagSummary(tag=tag, tag_type=tt, company_count=count) for (tag, tt), count in counts.items()]

    def get_company_ids_for_tag(self, tag: str, user_id: Optional[str]) -> list[str]:
        return [t.company_id for t in self._docs.values() if t.tag == tag and self._is_visible(t, user_id)]

    def list_tagged_companies(self, tag: str, user_id: Optional[str], page: int, size: int) -> tuple[int, list[str]]:
        ids = self.get_company_ids_for_tag(tag, user_id)
        offset = (page - 1) * size
        return len(ids), ids[offset : offset + size]


@pytest.fixture()
def stub_repo() -> StubTagRepository:
    return StubTagRepository()


@pytest.fixture()
def client(stub_repo: StubTagRepository) -> TestClient:
    app.dependency_overrides[get_tag_service] = lambda: TagService(repository=stub_repo)
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/tags
# ---------------------------------------------------------------------------


class TestApplyTag:
    def test_personal_tag_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/companies/ibm-id/tags",
            json={"tag": "competitors", "tag_type": "personal", "user_id": USER_ID},
        )
        assert response.status_code == 201

    def test_public_tag_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/companies/ibm-id/tags",
            json={"tag": "hot-prospect", "tag_type": "public"},
        )
        assert response.status_code == 201

    def test_response_contains_normalized_tag(self, client: TestClient) -> None:
        data = client.post(
            "/companies/ibm-id/tags",
            json={"tag": "Tech Leaders", "tag_type": "personal", "user_id": USER_ID},
        ).json()
        assert data["tag"] == "tech-leaders"
        assert data["company_id"] == "ibm-id"
        assert data["user_id"] == USER_ID
        assert data["tag_type"] == "personal"

    def test_personal_tag_without_user_id_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/companies/ibm-id/tags",
            json={"tag": "competitors", "tag_type": "personal"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /companies/{company_id}/tags/{tag}
# ---------------------------------------------------------------------------


class TestRemoveTag:
    def test_returns_204(self, client: TestClient) -> None:
        client.post(
            "/companies/ibm-id/tags",
            json={"tag": "targets", "tag_type": "personal", "user_id": USER_ID},
        )
        response = client.delete(f"/companies/ibm-id/tags/targets?tag_type=personal&user_id={USER_ID}")
        assert response.status_code == 204

    def test_removing_nonexistent_tag_returns_204(self, client: TestClient) -> None:
        response = client.delete(f"/companies/ibm-id/tags/ghost?tag_type=personal&user_id={USER_ID}")
        assert response.status_code == 204

    def test_removing_public_tag(self, client: TestClient) -> None:
        client.post("/companies/ibm-id/tags", json={"tag": "hot-prospect", "tag_type": "public"})
        response = client.delete("/companies/ibm-id/tags/hot-prospect?tag_type=public")
        assert response.status_code == 204

    def test_personal_tag_without_user_id_returns_422(self, client: TestClient) -> None:
        response = client.delete("/companies/ibm-id/tags/ghost?tag_type=personal")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /tags
# ---------------------------------------------------------------------------


class TestListTags:
    def test_returns_empty_list_no_public_tags(self, client: TestClient) -> None:
        response = client.get("/tags")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_public_tags_without_user_id(self, client: TestClient) -> None:
        client.post("/companies/c1/tags", json={"tag": "hot-prospect", "tag_type": "public"})
        tags = {t["tag"]: t["tag_type"] for t in client.get("/tags").json()}
        assert tags.get("hot-prospect") == "public"

    def test_returns_personal_and_public_tags_with_user_id(self, client: TestClient) -> None:
        client.post("/companies/c1/tags", json={"tag": "competitors", "tag_type": "personal", "user_id": USER_ID})
        client.post("/companies/c2/tags", json={"tag": "hot-prospect", "tag_type": "public"})
        tags = {t["tag"]: t["company_count"] for t in client.get(f"/tags?user_id={USER_ID}").json()}
        assert tags["competitors"] == 1
        assert tags["hot-prospect"] == 1

    def test_personal_tags_not_visible_to_other_users(self, client: TestClient) -> None:
        client.post(
            "/companies/c1/tags",
            json={"tag": "my-secret", "tag_type": "personal", "user_id": USER_ID},
        )
        tags = [t["tag"] for t in client.get("/tags?user_id=other-user").json()]
        assert "my-secret" not in tags


# ---------------------------------------------------------------------------
# GET /tags/{tag}/companies
# ---------------------------------------------------------------------------


class TestGetTaggedCompanies:
    def test_returns_personal_company_ids(self, client: TestClient) -> None:
        client.post("/companies/c1/tags", json={"tag": "targets", "tag_type": "personal", "user_id": USER_ID})
        client.post("/companies/c2/tags", json={"tag": "targets", "tag_type": "personal", "user_id": USER_ID})
        data = client.get(f"/tags/targets/companies?user_id={USER_ID}").json()
        assert data["total"] == 2
        assert set(data["company_ids"]) == {"c1", "c2"}

    def test_returns_public_tag_companies_without_user(self, client: TestClient) -> None:
        client.post("/companies/c1/tags", json={"tag": "hot-prospect", "tag_type": "public"})
        data = client.get("/tags/hot-prospect/companies").json()
        assert "c1" in data["company_ids"]

    def test_pagination(self, client: TestClient) -> None:
        for i in range(5):
            client.post(
                f"/companies/c{i}/tags",
                json={"tag": "big-list", "tag_type": "personal", "user_id": USER_ID},
            )
        data = client.get(f"/tags/big-list/companies?size=3&user_id={USER_ID}").json()
        assert len(data["company_ids"]) == 3
        assert data["total"] == 5
