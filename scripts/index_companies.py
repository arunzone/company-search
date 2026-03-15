"""Bulk index companies from CSV into OpenSearch.

Handles the 7M row dataset safely:
  - Pandas chunked reading (5 000 rows/chunk) — memory-safe
  - opensearch-py helpers.bulk — efficient multi-doc ingestion
  - Data cleaning: NaN → None, float years → int
  - Idempotent: index is deleted and recreated on each run (safe for initial load)
  - Progress reported via tqdm

Usage:
    python scripts/index_companies.py [--csv PATH] [--batch-size N] [--recreate]
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Generator

import pandas as pd
from opensearchpy import OpenSearch, helpers
from tqdm import tqdm

# Allow importing from src/ without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from company_search.config import settings  # noqa: E402
from company_search.infrastructure.opensearch.index_mapping import INDEX_MAPPING  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "companies_sorted.csv"
CHUNK_SIZE = 5_000
BULK_BATCH = 500


def get_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=settings.opensearch_verify_certs,
        ssl_show_warn=False,
        timeout=30,
    )


def ensure_index(client: OpenSearch, index: str, recreate: bool) -> None:
    """Create index with mapping. Optionally delete existing index first."""
    exists = client.indices.exists(index=index)
    if exists and recreate:
        logger.info("Deleting existing index '%s'", index)
        client.indices.delete(index=index)
        exists = False
    if not exists:
        logger.info("Creating index '%s'", index)
        client.indices.create(index=index, body=INDEX_MAPPING)
    else:
        logger.info("Index '%s' already exists — skipping creation", index)


def clean_row(row: dict) -> dict:
    """Normalise a raw CSV row into an indexable document."""
    year_raw = row.get("year founded")
    year = None
    if year_raw and not (isinstance(year_raw, float) and math.isnan(year_raw)):
        try:
            year = int(float(year_raw))
        except (ValueError, TypeError):
            year = None

    def nullable(val: object) -> object:
        if val is None:
            return None
        if isinstance(val, float) and math.isnan(val):
            return None
        return val or None

    return {
        "id": str(int(row["Unnamed: 0"])),
        "name": nullable(row.get("name")),
        "domain": nullable(row.get("domain")),
        "year_founded": year,
        "industry": nullable(row.get("industry")),
        "size_range": nullable(row.get("size range")),
        "locality": nullable(row.get("locality")),
        "country": nullable(row.get("country")),
        "linkedin_url": nullable(row.get("linkedin url")),
        "current_employee_estimate": _to_int(row.get("current employee estimate")),
        "total_employee_estimate": _to_int(row.get("total employee estimate")),
    }


def _to_int(val: object) -> int | None:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def generate_actions(csv_path: Path, index: str) -> Generator[dict, None, None]:
    """Yield OpenSearch bulk action dicts from the CSV."""
    for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False):
        for _, row in chunk.iterrows():
            doc = clean_row(row.to_dict())
            if not doc.get("name"):
                continue  # skip rows with no company name
            yield {
                "_index": index,
                "_id": doc["id"],
                "_source": doc,
            }


def run(csv_path: Path, recreate: bool) -> None:
    client = get_client()
    index = settings.opensearch_index

    logger.info("Connecting to OpenSearch at %s:%d", settings.opensearch_host, settings.opensearch_port)
    info = client.info()
    logger.info("OpenSearch version: %s", info["version"]["number"])

    ensure_index(client, index, recreate)

    total_rows = sum(1 for _ in open(csv_path)) - 1  # subtract header
    logger.info("Indexing %d rows from %s", total_rows, csv_path)

    indexed = 0
    errors = 0

    with tqdm(total=total_rows, unit="docs", desc="Indexing") as pbar:
        for ok, info in helpers.parallel_bulk(
            client,
            generate_actions(csv_path, index),
            chunk_size=BULK_BATCH,
            thread_count=4,
            raise_on_error=False,
        ):
            if ok:
                indexed += 1
            else:
                errors += 1
                logger.warning("Bulk index error: %s", info)
            pbar.update(1)

    logger.info("Done. indexed=%d errors=%d", indexed, errors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index companies CSV into OpenSearch")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to CSV file")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the index before indexing")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.csv.exists():
        logger.error("CSV not found: %s", args.csv)
        sys.exit(1)
    run(csv_path=args.csv, recreate=args.recreate)
