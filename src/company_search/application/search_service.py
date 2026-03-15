"""Application service — thin orchestrator between API and repository.

For Part 1 this is intentionally simple: validate, delegate, return.
It exists as a seam so Part 2 (NL understanding, caching) can be added
here without touching the API or infrastructure layers.
"""

from __future__ import annotations

import logging

from company_search.domain.models import SearchFilters, SearchResponse
from company_search.domain.ports import SearchRepository

logger = logging.getLogger(__name__)


class SearchService:
    """Orchestrates company search requests."""

    def __init__(self, repository: SearchRepository) -> None:
        """
        Args:
            repository: Concrete search backend (injected).
        """
        self._repository = repository

    def search(self, filters: SearchFilters, page: int, size: int) -> SearchResponse:
        """Execute a company search.

        Args:
            filters: Structured search parameters.
            page: 1-based page number.
            size: Results per page.

        Returns:
            Paginated SearchResponse.
        """
        logger.info(
            "search filters=%s page=%d size=%d",
            filters.model_dump(exclude_none=True),
            page,
            size,
        )
        return self._repository.search(filters, page, size)
