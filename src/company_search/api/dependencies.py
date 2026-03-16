"""FastAPI dependency injection wiring.

All service construction is centralised here.
Swapping a backend for a test double only requires changing this file.
"""

from __future__ import annotations

from functools import lru_cache

from company_search.application.search_service import SearchService
from company_search.application.tag_service import TagService
from company_search.infrastructure.opensearch.client import get_opensearch_client
from company_search.infrastructure.opensearch.repository import OpenSearchRepository
from company_search.infrastructure.opensearch.tag_repository import OpenSearchTagRepository


@lru_cache(maxsize=1)
def get_repository() -> OpenSearchRepository:
    """Return the shared OpenSearch repository instance."""
    return OpenSearchRepository(client=get_opensearch_client())


@lru_cache(maxsize=1)
def get_tag_repository() -> OpenSearchTagRepository:
    """Return the shared OpenSearch tag repository instance."""
    return OpenSearchTagRepository(client=get_opensearch_client())


@lru_cache(maxsize=1)
def get_tag_service() -> TagService:
    """Return the shared TagService instance."""
    return TagService(repository=get_tag_repository())


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Return the shared SearchService instance."""
    return SearchService(repository=get_repository(), tag_service=get_tag_service())

