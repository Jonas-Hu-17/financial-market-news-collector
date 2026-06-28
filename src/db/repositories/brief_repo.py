"""brief 与 brief_item 仓储。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import BriefRow, BriefItemRow


class BriefRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, row: BriefRow) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO brief (period_type, period_date, language, model, "
                "generated_at, status, market_view_text) VALUES (?,?,?,?,?,?,?)",
                (row.period_type, row.period_date, row.language, row.model,
                 row.generated_at, row.status, row.market_view_text),
            )
            return cur.lastrowid

    def get(self, id: int) -> Optional[BriefRow]:
        conn = self.db.connect()
        try:
            row = conn.execute("SELECT * FROM brief WHERE id = ?", (id,)).fetchone()
            return BriefRow(**dict(row)) if row else None
        finally:
            conn.close()

    def set_market_view(self, id: int, market_view_text: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE brief SET market_view_text=? WHERE id=?",
                (market_view_text, id),
            )


class BriefItemRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, row: BriefItemRow) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO brief_item (brief_id, story_id, rank, headline, "
                "summary, view_text, created_at) VALUES (?,?,?,?,?,?,?)",
                (row.brief_id, row.story_id, row.rank, row.headline,
                 row.summary, row.view_text, row.created_at),
            )
            return cur.lastrowid

    def list_for_brief(self, brief_id: int) -> list[BriefItemRow]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM brief_item WHERE brief_id=? ORDER BY rank",
                (brief_id,),
            ).fetchall()
            return [BriefItemRow(**dict(r)) for r in rows]
        finally:
            conn.close()
