"""Tag domain models — pure data structures, no external dependencies."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TagType(str, Enum):
    public = "public"
    personal = "personal"


class Tag(BaseModel):
    company_id: str
    tag: str
    tag_type: TagType
    user_id: Optional[str] = None  # None for public tags
    created_at: datetime


class TagSummary(BaseModel):
    tag: str
    tag_type: TagType
    company_ids: list[str]


class TagCreate(BaseModel):
    tag: str
    tag_type: TagType = TagType.personal
    user_id: Optional[str] = None  # required when tag_type=personal


class CompanyTagsResponse(BaseModel):
    total: int
    page: int
    size: int
    company_ids: list[str]
