from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from company_search.api.health_router import router as health_router
from company_search.api.router import router as search_router
from company_search.api.tag_router import router as tag_router
from company_search.config import settings
from company_search.observability.logging import RequestLoggingMiddleware, setup_logging
from company_search.observability.telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    setup_logging(level=settings.log_level)
    setup_telemetry()
    yield


app = FastAPI(
    title="Company Search API",
    description="Search 7M companies by name, industry, location, and founding year.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(health_router)
app.include_router(search_router)
app.include_router(tag_router)

FastAPIInstrumentor.instrument_app(app)
