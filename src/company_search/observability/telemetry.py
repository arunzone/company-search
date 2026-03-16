"""OpenTelemetry instrumentation — traces and metrics.

Traces:  one span per HTTP request, printed to console on completion.
         Includes http.method, http.route, http.status_code, duration.

Metrics: exposed at GET /metrics in Prometheus format (scraped on demand).
         Captured automatically by FastAPIInstrumentor:
           - http.server.request.duration  (histogram, milliseconds)
           - http.server.active_requests   (up-down counter)
"""

from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_RESOURCE = Resource.create({"service.name": "company-search"})


def setup_telemetry() -> None:
    """Initialize global tracer and meter providers."""
    _setup_traces()
    _setup_metrics()


def _setup_traces() -> None:
    provider = TracerProvider(resource=_RESOURCE)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def _setup_metrics() -> None:
    metrics.set_meter_provider(MeterProvider(resource=_RESOURCE, metric_readers=[PrometheusMetricReader()]))
