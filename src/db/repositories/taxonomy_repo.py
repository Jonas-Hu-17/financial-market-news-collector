"""taxonomy 仓储。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import TaxonomyRow


class TaxonomyRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, row: TaxonomyRow) -> int:
        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM taxonomy WHERE dimension=? AND code=?",
                (row.dimension, row.code),
            ).fetchone()
            if existing:
                return existing["id"]
            cur = conn.execute(
                "INSERT INTO taxonomy (dimension, code, label, sort_order) "
                "VALUES (?,?,?,?)",
                (row.dimension, row.code, row.label, row.sort_order),
            )
            return cur.lastrowid

    def get_id(self, dimension: str, code: str) -> Optional[int]:
        conn = self.db.connect()
        try:
            r = conn.execute(
                "SELECT id FROM taxonomy WHERE dimension=? AND code=?",
                (dimension, code),
            ).fetchone()
            return r["id"] if r else None
        finally:
            conn.close()

    def list_by_dimension(self, dimension: str) -> list[TaxonomyRow]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM taxonomy WHERE dimension=? ORDER BY sort_order, id",
                (dimension,),
            ).fetchall()
            return [TaxonomyRow(**dict(r)) for r in rows]
        finally:
            conn.close()
