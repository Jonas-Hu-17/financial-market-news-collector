"""摄取服务：映射并幂等落库，挡住重复（在任何模型调用之前）。"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from src.models import ContentItem
from src.db.repositories.raw_item_repo import RawItemRepo
from .mapper import to_raw_item


@dataclass
class IngestStats:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0


class IngestionService:
    def __init__(self, repo: RawItemRepo):
        self.repo = repo

    def ingest(self, items: list[ContentItem], source_id: Optional[int] = None) -> IngestStats:
        stats = IngestStats(fetched=len(items))
        for item in items:
            _id, is_new = self.repo.upsert(to_raw_item(item, source_id))
            if is_new:
                stats.inserted += 1
            else:
                stats.skipped += 1
        return stats
