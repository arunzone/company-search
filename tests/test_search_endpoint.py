"""Integration-style tests for the search endpoint.

Uses a stub repository — no OpenSearch required.
Tests that the API layer correctly wires params → filters → response.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from company_search.application.search_service import SearchService
from company_search.domain.models import SearchFilters, SearchResponse, SearchResult
from company_search.domain.ports import SearchRepository
from company_search.main import app
from company_search.api.dependencies import get_search_service


# ---------------------------------------------------------------------------
# Stub repository — captures what filters were passed
# ---------------------------------------------------------------------------

class StubRepository:
    """In-memory stub that satisfies the SearchRepository protocol."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self.last_filters: SearchFilters | None = None
        self._results = results or []

    def search(self, filters: SearchFilters, page: int, size: int) -> SearchResponse:
        self.last_filters = filters
        return SearchResponse(
            total=len(self._results),
            page=page,
            size=size,
            results=self._results[:size],
        )


def _make_result(**kwargs) -> SearchResult:
    defaults = dict(id="1", name="Acme Corp", industry="internet", score=1.0)
    return SearchResult(**(defaults | kwargs))


@pytest.fixture()
def stub_repo() -> StubRepository:
    return StubRepository(results=[_make_result()])


@pytest.fixture()
def client(stub_repo: StubRepository) -> TestClient:
    app.dependency_overrides[get_search_service] = lambda: SearchService(repository=stub_repo)
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    def test_returns_200_with_no_params(self, client: TestClient):
        response = client.get("/companies/search")
        assert response.status_code == 200

    def test_response_shape(self, client: TestClient):
        response = client.get("/companies/search")
        data = response.json()
        assert "total" in data
        assert "results" in data
        assert "page" in data
        assert "size" in data

    def test_name_param_is_passed_to_filters(self, client: TestClient, stub_repo: StubRepository):
        client.get("/companies/search?name=acme")
        assert stub_repo.last_filters.name == "acme"

    def test_industry_param_is_passed_to_filters(self, client: TestClient, stub_repo: StubRepository):
        client.get("/companies/search?industry=internet")
        assert stub_repo.last_filters.industry == "internet"

    def test_location_param_is_passed_to_filters(self, client: TestClient, stub_repo: StubRepository):
        client.get("/companies/search?location=california")
        assert stub_repo.last_filters.location == "california"

    def test_year_range_params(self, client: TestClient, stub_repo: StubRepository):
        client.get("/companies/search?founded_year_min=2000&founded_year_max=2010")
        assert stub_repo.last_filters.founded_year_min == 2000
        assert stub_repo.last_filters.founded_year_max == 2010

    def test_invalid_year_range_returns_422(self, client: TestClient):
        response = client.get("/companies/search?founded_year_min=2020&founded_year_max=2010")
        assert response.status_code == 422

    def test_pagination_defaults(self, client: TestClient, stub_repo: StubRepository):
        client.get("/companies/search")
        # page and size defaults
        response = client.get("/companies/search")
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10

    def test_size_over_100_returns_422(self, client: TestClient):
        response = client.get("/companies/search?size=200")
        assert response.status_code == 422

    def test_results_list_in_response(self, client: TestClient):
        response = client.get("/companies/search?name=acme")
        data = response.json()
        assert isinstance(data["results"], list)
        assert data["results"][0]["name"] == "Acme Corp"
