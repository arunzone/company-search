"""Structured JSON logging and request-level observability.

Logging emits JSON lines so log aggregators (Datadog, CloudWatch, etc.)
can parse fields directly without regex. Each request gets a latency log
with method, path, status, and latency as top-level JSON fields.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_RESERVED_LOG_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Any fields passed via ``extra=`` are merged into the top-level JSON object,
    making them directly queryable by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        # Merge any extra fields that were not part of the standard LogRecord
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and not key.startswith("_"):
                log[key] = value
        return json.dumps(log)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger to emit structured JSON.

    Args:
        level: Logging level string, e.g. "INFO" or "DEBUG".
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Silence noisy third-party loggers
    for noisy in ("opensearchpy", "urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_access_logger = logging.getLogger("company_search.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with method, path, status, and wall-clock latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        _access_logger.info(
            "%s %s %d",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response
