"""Domain ports — define what the application layer needs from infrastructure.

Using typing.Protocol (structural typing) so implementations require no
inheritance, keeping infrastructure decoupled from the domain.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from company_search.domain.models import SearchFilters, SearchResponse


@runtime_checkable
class SearchRepository(Protocol):
    """Contract for executing a company search against a backend store."""

    def search(self, filters: SearchFilters, page: int, size: int) -> SearchResponse:
        """Execute search and return a paginated response.

        Args:
            filters: Structured search parameters.
            page: 1-based page number.
            size: Number of results per page.

        Returns:
            Paginated SearchResponse with scored results.
        """
        ...
