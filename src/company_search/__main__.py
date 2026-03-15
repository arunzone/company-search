import uvicorn

from company_search.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "company_search.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=False,
    )
