"""event / feedback 仓储（匿名 anon_id）。"""
from __future__ import annotations
from datetime import datetime, timezone
from ..database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, brief_item_id: int, type: str, anon_id: str,
            ts: str | None = None) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO event (brief_item_id, type, anon_id, ts) "
                "VALUES (?,?,?,?)",
                (brief_item_id, type, anon_id, ts or _now()),
            )
            return cur.lastrowid


class FeedbackRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, brief_item_id: int, rating: str, anon_id: str,
            comment: str | None = None, ts: str | None = None) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO feedback (brief_item_id, rating, comment, anon_id, ts) "
                "VALUES (?,?,?,?,?)",
                (brief_item_id, _rating_to_int(rating), comment, anon_id,
                 ts or _now()),
            )
            return cur.lastrowid

    def upsert_rating(self, brief_item_id: int, rating: str,
                      anon_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM feedback WHERE brief_item_id=? AND anon_id=? "
                "AND comment IS NULL",
                (brief_item_id, anon_id),
            )
            conn.execute(
                "INSERT INTO feedback (brief_item_id, rating, anon_id, ts) "
                "VALUES (?,?,?,?)",
                (brief_item_id, _rating_to_int(rating), anon_id, _now()),
            )

    def counts(self, brief_item_id: int) -> dict:
        conn = self.db.connect()
        try:
            up = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE brief_item_id=? "
                "AND rating=1",
                (brief_item_id,)).fetchone()[0]
            down = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE brief_item_id=? "
                "AND rating=-1",
                (brief_item_id,)).fetchone()[0]
            return {"up": up, "down": down}
        finally:
            conn.close()


def _rating_to_int(rating: str) -> int:
    return 1 if rating == "up" else -1
