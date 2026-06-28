import sqlite3
from pathlib import Path

SCHEMA = Path("src/db/schema.sql").read_text(encoding="utf-8")


def test_schema_creates_core_tables():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    expected = {
        "source", "raw_item", "story", "story_member", "score", "enrichment",
        "taxonomy", "story_tag", "entity", "story_entity", "brief", "brief_item",
        "watchlist_item", "app_user", "subscription", "delivery", "event", "feedback",
    }
    assert expected <= names


def test_raw_item_dedup_key_unique():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO raw_item (title, fetched_at, dedup_key) VALUES (?,?,?)",
        ("a", "2026-06-28T00:00:00Z", "key1"),
    )
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO raw_item (title, fetched_at, dedup_key) VALUES (?,?,?)",
            ("b", "2026-06-28T00:00:00Z", "key1"),
        )
