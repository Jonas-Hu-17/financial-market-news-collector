"""raw_item 仓储：按 dedup_key 幂等 upsert，实现全局持久化去重。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import RawItemRow

_COLS = [
    "source_id", "external_id", "url", "canonical_url", "title", "summary",
    "author", "published_at", "fetched_at", "dedup_key", "content_hash",
    "language", "raw_payload",
]


class RawItemRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, item: RawItemRow) -> tuple[int, bool]:
        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM raw_item WHERE dedup_key = ?", (item.dedup_key,)
            ).fetchone()
            if existing is not None:
                return existing["id"], False
            placeholders = ", ".join("?" for _ in _COLS)
            values = [getattr(item, c) for c in _COLS]
            cur = conn.execute(
                f"INSERT INTO raw_item ({', '.join(_COLS)}) VALUES ({placeholders})",
                values,
            )
            return cur.lastrowid, True

    def get(self, id: int) -> Optional[RawItemRow]:
        conn = self.db.connect()
        try:
            row = conn.execute("SELECT * FROM raw_item WHERE id = ?", (id,)).fetchone()
            return RawItemRow(**dict(row)) if row else None
        finally:
            conn.close()

    def get_by_dedup_key(self, key: str) -> Optional[RawItemRow]:
        conn = self.db.connect()
        try:
            row = conn.execute(
                "SELECT * FROM raw_item WHERE dedup_key = ?", (key,)
            ).fetchone()
            return RawItemRow(**dict(row)) if row else None
        finally:
            conn.close()
