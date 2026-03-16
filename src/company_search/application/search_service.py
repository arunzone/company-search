"""Application service — thin orchestrator between API and repository.

For Part 1 this is intentionally simple: validate, delegate, return.
It exists as a seam so Part 2 (NL understanding, caching) can be added
here without touching the API or infrastructure layers.
"""

from __future__ import annotations

import logging

from company_search.application.tag_service import TagService
from company_search.domain.models import SearchFilters, SearchResponse
from company_search.domain.ports import SearchRepository
from company_search.domain.tag_models import TagType

logger = logging.getLogger(__name__)


class SearchService:
    """Orchestrates company search requests."""

    def __init__(self, repository: SearchRepository, tag_service: TagService) -> None:
        self._repository = repository
        self._tag_service = tag_service

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
        personal_tags = []
        shared_tags = []
        if TagType.personal in filters.tags:
            personal_tags = self._tag_service.list_tags(user_id=filters.user_id)
        elif TagType.public in filters.tags:
            shared_tags = self._tag_service.list_tags()
        tags = personal_tags + shared_tags    
        nested_company_ids = [tag.company_ids for tag in tags]
        company_ids = [item for company_id_list in nested_company_ids for item in company_id_list]
        filters.company_ids = list(set(company_ids))
        
        return self._repository.search(filters, page, size)
