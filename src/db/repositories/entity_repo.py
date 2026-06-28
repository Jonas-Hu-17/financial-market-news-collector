"""entity、story_entity、watchlist_item 仓储。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import EntityRow


class EntityRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, row: EntityRow) -> int:
        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM entity WHERE type=? AND name=?",
                (row.type, row.name),
            ).fetchone()
            if existing:
                return existing["id"]
            cur = conn.execute(
                "INSERT INTO entity (type, name, ticker, identifiers, created_at) "
                "VALUES (?,?,?,?,?)",
                (row.type, row.name, row.ticker, row.identifiers, row.created_at),
            )
            return cur.lastrowid

    def get(self, id: int) -> Optional[EntityRow]:
        conn = self.db.connect()
        try:
            row = conn.execute("SELECT * FROM entity WHERE id = ?", (id,)).fetchone()
            return EntityRow(**dict(row)) if row else None
        finally:
            conn.close()


class StoryEntityRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, story_id: int, entity_id: int, role: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO story_entity (story_id, entity_id, role) VALUES (?,?,?)",
                (story_id, entity_id, role),
            )

    def stories_for_entity(self, entity_id: int) -> list[int]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT story_id FROM story_entity WHERE entity_id = ?",
                (entity_id,),
            ).fetchall()
            return [r["story_id"] for r in rows]
        finally:
            conn.close()


class WatchlistRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, entity_id: int, note: str, added_at: str, user_id: int = 1) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO watchlist_item (user_id, entity_id, note, added_at) "
                "VALUES (?,?,?,?)",
                (user_id, entity_id, note, added_at),
            )
            return cur.lastrowid

    def list(self, user_id: int = 1) -> list[int]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT entity_id FROM watchlist_item WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            return [r["entity_id"] for r in rows]
        finally:
            conn.close()
