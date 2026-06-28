"""为 Web 反馈/埋点补列（幂等迁移）。"""
from __future__ import annotations
from .database import Database


def ensure_web_columns(db: Database) -> None:
    with db.transaction() as conn:
        for table in ("event", "feedback"):
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if "anon_id" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN anon_id TEXT")
