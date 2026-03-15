"""OpenSearch connection factory.

Returns a single shared client instance (cached via lru_cache).
The connection pool is sized for 60 RPS: pool_size ≥ RPS × avg_latency_s.
Assuming p99 latency ~200ms → pool_size = 60 × 0.2 = 12, we use 25 for headroom.
"""

from functools import lru_cache

from opensearchpy import OpenSearch

from company_search.config import settings


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    """Return the shared OpenSearch client, creating it on first call.

    Returns:
        A configured OpenSearch client with connection pooling.
    """
    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=settings.opensearch_verify_certs,
        ssl_show_warn=False,
        maxsize=25,
        timeout=10,
        max_retries=2,
        retry_on_timeout=True,
    )
