"""OpenSearch implementation of the SearchRepository port.

Knows about OpenSearch DSL and the opensearch-py client.
Nothing above this layer does.
"""

from __future__ import annotations

import logging
from typing import Any

from opensearchpy import OpenSearch

from company_search.config import settings
from company_search.domain.models import SearchFilters, SearchResponse, SearchResult
from company_search.domain.query_builder import build_search_body

logger = logging.getLogger(__name__)


class OpenSearchRepository:
    """Concrete SearchRepository backed by OpenSearch."""

    def __init__(self, client: OpenSearch) -> None:
        self._client = client
        self._index = settings.opensearch_index

    def search(self, filters: SearchFilters, page: int, size: int) -> SearchResponse:
        """Execute search against OpenSearch and return domain results.

        Args:
            filters: Structured search parameters.
            page: 1-based page number.
            size: Results per page.

        Returns:
            SearchResponse with matched companies and total count.

        Raises:
            RuntimeError: If the OpenSearch request fails.
        """
        body = build_search_body(filters, page, size)
        logger.debug("opensearch_query index=%s body=%s", self._index, body)

        try:
            raw = self._client.search(index=self._index, body=body)
        except Exception as exc:
            logger.exception("OpenSearch search failed")
            raise RuntimeError(f"Search execution failed: {exc}") from exc

        return self._map_response(raw, page, size)

    def _map_response(self, raw: dict[str, Any], page: int, size: int) -> SearchResponse:
        total = raw["hits"]["total"]["value"]
        results = [self._map_hit(hit) for hit in raw["hits"]["hits"]]
        return SearchResponse(total=total, page=page, size=size, results=results)

    @staticmethod
    def _map_hit(hit: dict[str, Any]) -> SearchResult:
        source = hit.get("_source", {})
        return SearchResult(
            id=hit.get("_id", source.get("id", "")),
            name=source.get("name", ""),
            domain=source.get("domain"),
            year_founded=source.get("year_founded"),
            industry=source.get("industry"),
            size_range=source.get("size_range"),
            locality=source.get("locality"),
            country=source.get("country"),
            linkedin_url=source.get("linkedin_url"),
            score=hit.get("_score") or 0.0,
        )
