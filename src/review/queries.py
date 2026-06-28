"""跨期回顾查询：按分类维度、按 watchlist 公司。"""
from __future__ import annotations
from ..db.database import Database


class ReviewQuery:
    def __init__(self, db: Database):
        self.db = db

    def by_taxonomy(self, dimension: str, code: str, limit: int = 50) -> list[dict]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                """SELECT b.period_date, bi.rank, bi.headline, bi.view_text,
                          bi.story_id
                   FROM brief_item bi
                   JOIN brief b ON b.id = bi.brief_id
                   JOIN story_tag st ON st.story_id = bi.story_id
                   JOIN taxonomy t ON t.id = st.taxonomy_id
                   WHERE t.dimension = ? AND t.code = ?
                   ORDER BY b.period_date DESC, bi.rank ASC LIMIT ?""",
                (dimension, code, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def by_entity(self, entity_id: int, limit: int = 100) -> list[dict]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                """SELECT b.period_date, bi.rank, bi.headline, bi.view_text,
                          bi.story_id
                   FROM brief_item bi
                   JOIN brief b ON b.id = bi.brief_id
                   JOIN story_entity se ON se.story_id = bi.story_id
                   WHERE se.entity_id = ?
                   ORDER BY b.period_date DESC, bi.rank ASC LIMIT ?""",
                (entity_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
