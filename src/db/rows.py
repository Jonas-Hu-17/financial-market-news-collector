"""Pydantic 行模型，与 schema.sql 各表列对齐。id 为空表示尚未入库。"""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel


class RawItemRow(BaseModel):
    id: Optional[int] = None
    source_id: Optional[int] = None
    external_id: Optional[str] = None
    url: Optional[str] = None
    canonical_url: Optional[str] = None
    title: str
    summary: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    fetched_at: str
    dedup_key: str
    content_hash: Optional[str] = None
    language: Optional[str] = None
    raw_payload: Optional[str] = None


class StoryRow(BaseModel):
    id: Optional[int] = None
    canonical_title: str
    dedup_cluster_key: Optional[str] = None
    first_seen_at: str
    last_seen_at: str
    last_update_at: Optional[str] = None
    status: str = "new"


class ScoreRow(BaseModel):
    id: Optional[int] = None
    story_id: int
    model: Optional[str] = None
    score: float
    importance_rationale: Optional[str] = None
    scored_at: str


class TaxonomyRow(BaseModel):
    id: Optional[int] = None
    dimension: str
    code: str
    label: str
    sort_order: int = 0


class EntityRow(BaseModel):
    id: Optional[int] = None
    type: str
    name: str
    ticker: Optional[str] = None
    identifiers: Optional[str] = None
    created_at: str


class BriefRow(BaseModel):
    id: Optional[int] = None
    period_type: str
    period_date: str
    language: str = "zh"
    model: Optional[str] = None
    generated_at: str
    status: str = "draft"
    market_view_text: Optional[str] = None


class BriefItemRow(BaseModel):
    id: Optional[int] = None
    brief_id: int
    story_id: int
    rank: int
    headline: Optional[str] = None
    summary: Optional[str] = None
    view_text: Optional[str] = None
    created_at: str
