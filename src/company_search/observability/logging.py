"""Structured JSON logging and request-level observability.

Logging emits JSON lines so log aggregators (Datadog, CloudWatch, etc.)
can parse fields directly without regex. Each request gets a latency log.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with method, path, status, and wall-clock latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        logging.getLogger("company_search.access").info(
            json.dumps(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "status": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                }
            )
        )
        return response
