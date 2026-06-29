"""幂等迁移：补列、补索引。"""
from __future__ import annotations
from .database import Database


def ensure_web_columns(db: Database) -> None:
    with db.transaction() as conn:
        for table in ("event", "feedback"):
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if "anon_id" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN anon_id TEXT")


def ensure_indexes(db: Database) -> None:
    """幂等补建性能关键索引（兼容已存在的库）。"""
    with db.transaction() as conn:
        # clusterer 反向直查：从 raw_item_id 直接找到所属 story
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_story_member_raw "
            "ON story_member(raw_item_id)"
        )
