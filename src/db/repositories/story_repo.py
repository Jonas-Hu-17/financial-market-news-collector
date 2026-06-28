"""story 与 story_member 仓储。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import StoryRow


class StoryRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, row: StoryRow) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO story (canonical_title, dedup_cluster_key, "
                "first_seen_at, last_seen_at, last_update_at, status) "
                "VALUES (?,?,?,?,?,?)",
                (row.canonical_title, row.dedup_cluster_key, row.first_seen_at,
                 row.last_seen_at, row.last_update_at, row.status),
            )
            return cur.lastrowid

    def get(self, id: int) -> Optional[StoryRow]:
        conn = self.db.connect()
        try:
            row = conn.execute("SELECT * FROM story WHERE id = ?", (id,)).fetchone()
            return StoryRow(**dict(row)) if row else None
        finally:
            conn.close()

    def update_status(self, id: int, status: str, last_update_at: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE story SET status=?, last_update_at=? WHERE id=?",
                (status, last_update_at, id),
            )

    def recent(self, since_iso: str) -> list[StoryRow]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM story WHERE last_seen_at >= ? ORDER BY last_seen_at DESC",
                (since_iso,),
            ).fetchall()
            return [StoryRow(**dict(r)) for r in rows]
        finally:
            conn.close()


class StoryMemberRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, story_id: int, raw_item_id: int, is_primary: bool = False) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO story_member (story_id, raw_item_id, is_primary) "
                "VALUES (?,?,?)",
                (story_id, raw_item_id, int(is_primary)),
            )

    def raw_items_for_story(self, story_id: int) -> list[int]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT raw_item_id FROM story_member WHERE story_id = ?",
                (story_id,),
            ).fetchall()
            return [r["raw_item_id"] for r in rows]
        finally:
            conn.close()
