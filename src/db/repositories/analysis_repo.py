"""score、enrichment、story_tag 仓储。"""
from __future__ import annotations
from typing import Optional
from ..database import Database
from ..rows import ScoreRow


class ScoreRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, row: ScoreRow) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO score (story_id, model, score, importance_rationale, scored_at) "
                "VALUES (?,?,?,?,?)",
                (row.story_id, row.model, row.score, row.importance_rationale, row.scored_at),
            )
            return cur.lastrowid

    def latest_for_story(self, story_id: int) -> Optional[ScoreRow]:
        conn = self.db.connect()
        try:
            row = conn.execute(
                "SELECT * FROM score WHERE story_id=? ORDER BY scored_at DESC LIMIT 1",
                (story_id,),
            ).fetchone()
            return ScoreRow(**dict(row)) if row else None
        finally:
            conn.close()


class EnrichmentRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, story_id: int, context_text: str,
            corroborating_sources: str, confidence: str, created_at: str) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO enrichment (story_id, context_text, corroborating_sources, "
                "confidence, created_at) VALUES (?,?,?,?,?)",
                (story_id, context_text, corroborating_sources, confidence, created_at),
            )
            return cur.lastrowid


class StoryTagRepo:
    def __init__(self, db: Database):
        self.db = db

    def add(self, story_id: int, taxonomy_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO story_tag (story_id, taxonomy_id) VALUES (?,?)",
                (story_id, taxonomy_id),
            )

    def taxonomy_ids_for_story(self, story_id: int) -> list[int]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT taxonomy_id FROM story_tag WHERE story_id = ?",
                (story_id,),
            ).fetchall()
            return [r["taxonomy_id"] for r in rows]
        finally:
            conn.close()
