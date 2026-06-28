"""SQLite 连接封装，加载 sqlite-vec 并应用 schema。"""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import sqlite_vec

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# 与 embedding 模型维度一致（paraphrase-multilingual-MiniLM-L12-v2 = 384）
EMBEDDING_DIM = 384


class Database:
    def __init__(self, path: str = "data/marketnews.db"):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_schema(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_raw_item "
                f"USING vec0(embedding float[{EMBEDDING_DIM}])"
            )
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
