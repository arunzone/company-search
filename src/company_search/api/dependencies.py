"""FastAPI dependency injection wiring.

All service construction is centralised here.
Swapping OpenSearch for a test double only requires changing this file.
"""

from __future__ import annotations

from functools import lru_cache

from company_search.application.search_service import SearchService
from company_search.infrastructure.opensearch.client import get_opensearch_client
from company_search.infrastructure.opensearch.repository import OpenSearchRepository


@lru_cache(maxsize=1)
def get_repository() -> OpenSearchRepository:
    """Return the shared OpenSearch repository instance."""
    return OpenSearchRepository(client=get_opensearch_client())


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Return the shared SearchService instance."""
    return SearchService(repository=get_repository())
