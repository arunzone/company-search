"""Index mapping for the user_company_tags sidecar index.

Design:
  - Separate from the 7M companies index — tag writes never touch company docs.
  - tag_type field distinguishes public (shared) from personal (per-user) tags.
  - Document ID: "{tag_type}|{user_id or 'public'}|{company_id}|{tag}" — idempotent apply.
  - Phase 3 extension: add tag_raw field alongside tag (the canonical form)
    when AI normalization is introduced.
"""

TAG_INDEX = "user_company_tags"

TAG_INDEX_MAPPING: dict = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            "user_id": {"type": "keyword"},
            "company_id": {"type": "keyword"},
            "tag": {"type": "keyword"},
            "tag_type": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    },
}
