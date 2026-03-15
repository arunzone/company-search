"""Unit tests for the query builder — no I/O, no mocking needed."""

import pytest

from company_search.domain.models import SearchFilters
from company_search.domain.query_builder import build_search_body, _build_must, _build_filters


class TestBuildMust:
    def test_no_name_returns_match_all(self):
        result = _build_must(None)
        assert result == [{"match_all": {}}]

    def test_name_returns_multi_match(self):
        result = _build_must("ibm")
        assert len(result) == 1
        assert "multi_match" in result[0]
        assert result[0]["multi_match"]["query"] == "ibm"
        assert result[0]["multi_match"]["fuzziness"] == "AUTO"


class TestBuildFilters:
    def test_empty_filters_returns_no_clauses(self):
        filters = SearchFilters()
        assert _build_filters(filters) == []

    def test_industry_filter(self):
        filters = SearchFilters(industry="computer software")
        clauses = _build_filters(filters)
        assert any("term" in c and c["term"] == {"industry.keyword": "computer software"} for c in clauses)

    def test_location_filter_uses_bool_should(self):
        filters = SearchFilters(location="california")
        clauses = _build_filters(filters)
        assert len(clauses) == 1
        assert "bool" in clauses[0]
        should = clauses[0]["bool"]["should"]
        fields = [list(c["match"].keys())[0] for c in should]
        assert "locality" in fields
        assert "country" in fields

    def test_year_range_filter_min_only(self):
        filters = SearchFilters(founded_year_min=2000)
        clauses = _build_filters(filters)
        range_clause = next(c for c in clauses if "range" in c)
        assert range_clause["range"]["year_founded"]["gte"] == 2000
        assert "lte" not in range_clause["range"]["year_founded"]

    def test_year_range_filter_both_bounds(self):
        filters = SearchFilters(founded_year_min=2000, founded_year_max=2010)
        clauses = _build_filters(filters)
        range_clause = next(c for c in clauses if "range" in c)
        assert range_clause["range"]["year_founded"] == {"gte": 2000, "lte": 2010}

    def test_size_range_filter(self):
        filters = SearchFilters(size_range="10001+")
        clauses = _build_filters(filters)
        assert {"term": {"size_range": "10001+"}} in clauses

    def test_all_filters_combined(self):
        filters = SearchFilters(
            industry="internet",
            location="new york",
            founded_year_min=2005,
            founded_year_max=2015,
            size_range="51-200",
        )
        clauses = _build_filters(filters)
        assert len(clauses) == 4  # industry, location, year range, size


class TestBuildSearchBody:
    def test_pagination_offset(self):
        filters = SearchFilters()
        body = build_search_body(filters, page=3, size=10)
        assert body["from"] == 20
        assert body["size"] == 10

    def test_source_fields_are_present(self):
        body = build_search_body(SearchFilters(), page=1, size=5)
        assert "name" in body["_source"]
        assert "industry" in body["_source"]

    def test_track_total_hits(self):
        body = build_search_body(SearchFilters(), page=1, size=5)
        assert body["track_total_hits"] is True
