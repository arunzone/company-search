"""OpenSearch implementation of the TagRepository port."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import logging

from opensearchpy import OpenSearch

from company_search.domain.tag_models import Tag, TagSummary, TagType
from company_search.infrastructure.opensearch.tag_index_mapping import TAG_INDEX, TAG_INDEX_MAPPING

_MAX_TAG_IDS = 10_000  # upper bound for search filter lookups
_log = logging.getLogger(__name__)


def _ensure_index(client: OpenSearch) -> None:
    if not client.indices.exists(index=TAG_INDEX):
        client.indices.create(index=TAG_INDEX, body=TAG_INDEX_MAPPING, ignore=400)
        return
    resp = client.indices.put_mapping(index=TAG_INDEX, body=TAG_INDEX_MAPPING["mappings"], ignore=400)
    if isinstance(resp, dict) and resp.get("status") == 400:
        _log.warning("Tag index mapping conflict — dropping and recreating %s", TAG_INDEX)
        client.indices.delete(index=TAG_INDEX)
        client.indices.create(index=TAG_INDEX, body=TAG_INDEX_MAPPING, ignore=400)


def _doc_id(tag_type: TagType, user_id: Optional[str], company_id: str, tag: str) -> str:
    return f"{tag_type.value}|{user_id or 'public'}|{company_id}|{tag}"


def _tag_filter(tag: str, user_id: Optional[str]) -> dict[str, Any]:
    public_clause: dict[str, Any] = {"bool": {"filter": [{"term": {"tag_type": "public"}}, {"term": {"tag": tag}}]}}
    if user_id is None:
        return public_clause
    personal_clause: dict[str, Any] = {
        "bool": {
            "filter": [
                {"term": {"tag_type": "personal"}},
                {"term": {"user_id": user_id}},
                {"term": {"tag": tag}},
            ]
        }
    }
    return {"bool": {"should": [public_clause, personal_clause], "minimum_should_match": 1}}


def _list_query(user_id: Optional[str]) -> dict[str, Any]:
    if user_id is None:
        return {"term": {"tag_type": "public"}}
    return {
        "bool": {
            "should": [
                {"term": {"tag_type": "public"}},
                {"bool": {"filter": [{"term": {"tag_type": "personal"}}, {"term": {"user_id": user_id}}]}},
            ],
            "minimum_should_match": 1,
        }
    }


def _parse_tag_summaries(raw: dict[str, Any]) -> list[TagSummary]:
    buckets = raw["aggregations"]["by_tag"]["buckets"]
    return [
        TagSummary(tag=b["key"]["tag"], tag_type=TagType(b["key"]["tag_type"]), company_count=b["doc_count"])
        for b in buckets
    ]


class OpenSearchTagRepository:
    """Concrete TagRepository backed by a dedicated OpenSearch index."""

    def __init__(self, client: OpenSearch) -> None:
        self._client = client
        _ensure_index(client)

    def add_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> Tag:
        now = datetime.now(timezone.utc)
        self._client.index(
            index=TAG_INDEX,
            id=_doc_id(tag_type, user_id, company_id, tag),
            body={
                "user_id": user_id,
                "company_id": company_id,
                "tag": tag,
                "tag_type": tag_type.value,
                "created_at": now.isoformat(),
            },
            refresh=True,
        )
        return Tag(user_id=user_id, company_id=company_id, tag=tag, tag_type=tag_type, created_at=now)

    def remove_tag(self, company_id: str, tag: str, tag_type: TagType, user_id: Optional[str]) -> None:
        self._client.delete(
            index=TAG_INDEX,
            id=_doc_id(tag_type, user_id, company_id, tag),
            ignore=[404],
        )

    def list_tags(self, user_id: Optional[str]) -> list[TagSummary]:
        body: dict[str, Any] = {
            "query": _list_query(user_id),
            "size": 0,
            "aggs": {
                "by_tag": {
                    "composite": {
                        "size": 200,
                        "sources": [
                            {"tag": {"terms": {"field": "tag"}}},
                            {"tag_type": {"terms": {"field": "tag_type"}}},
                        ],
                    }
                }
            },
        }
        raw = self._client.search(index=TAG_INDEX, body=body)
        return _parse_tag_summaries(raw)

    def get_company_ids_for_tag(self, tag: str, user_id: Optional[str]) -> list[str]:
        body: dict[str, Any] = {
            "query": _tag_filter(tag, user_id),
            "_source": ["company_id"],
            "size": _MAX_TAG_IDS,
        }
        raw = self._client.search(index=TAG_INDEX, body=body)
        return [hit["_source"]["company_id"] for hit in raw["hits"]["hits"]]

    def list_tagged_companies(self, tag: str, user_id: Optional[str], page: int, size: int) -> tuple[int, list[str]]:
        body: dict[str, Any] = {
            "query": _tag_filter(tag, user_id),
            "_source": ["company_id"],
            "from": (page - 1) * size,
            "size": size,
            "track_total_hits": True,
        }
        raw = self._client.search(index=TAG_INDEX, body=body)
        total = raw["hits"]["total"]["value"]
        return total, [hit["_source"]["company_id"] for hit in raw["hits"]["hits"]]
