"""Health and metrics endpoints.

GET /health   — liveness + OpenSearch cluster status
GET /metrics  — Prometheus metrics (request count, latency, active requests)
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from company_search.infrastructure.opensearch.client import get_opensearch_client

router = APIRouter(tags=["observability"])


@router.get("/health")
def health() -> dict:
    """Return service liveness and OpenSearch cluster health."""
    try:
        os_status: str = get_opensearch_client().cluster.health().get("status", "unknown")
    except Exception:
        os_status = "error"
    return {
        "status": "ok" if os_status in ("green", "yellow") else "degraded",
        "opensearch": os_status,
    }


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    """Prometheus metrics: request count, latency histogram, active requests."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
