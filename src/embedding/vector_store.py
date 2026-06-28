"""sqlite-vec 向量表读写封装。"""
from __future__ import annotations
import struct
from typing import Optional
from ..db.database import Database


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class VectorStore:
    def __init__(self, db: Database):
        self.db = db

    def add(self, raw_item_id: int, vector: list[float]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM vec_raw_item WHERE rowid=?", (raw_item_id,))
            conn.execute(
                "INSERT INTO vec_raw_item(rowid, embedding) VALUES (?, ?)",
                (raw_item_id, _pack(vector)),
            )

    def knn(self, vector: list[float], k: int,
            allowed_ids: Optional[set[int]] = None) -> list[tuple[int, float]]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT rowid, distance FROM vec_raw_item "
                "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                (_pack(vector), k if allowed_ids is None else max(k, 50)),
            ).fetchall()
            out = [(r["rowid"], r["distance"]) for r in rows]
            if allowed_ids is not None:
                out = [t for t in out if t[0] in allowed_ids]
            return out[:k]
        finally:
            conn.close()
