from src.db.database import Database


def test_init_schema_and_foreign_keys(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    conn = db.connect()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "raw_item" in tables


EMBEDDING_DIM = 384


def _make_vec(first_val: float, second_val: float = 0.0) -> bytes:
    """Construct a 384-dim vector with first two components set, rest zero."""
    import struct
    v = [0.0] * EMBEDDING_DIM
    v[0] = first_val
    v[1] = second_val
    return struct.pack(f"{EMBEDDING_DIM}f", *v)


def test_vec_table_knn(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    conn = db.connect()
    conn.execute("INSERT INTO vec_raw_item(rowid, embedding) VALUES (?, ?)",
                 (1, _make_vec(1.0, 0.0)))
    conn.execute("INSERT INTO vec_raw_item(rowid, embedding) VALUES (?, ?)",
                 (2, _make_vec(0.0, 1.0)))
    conn.commit()
    rows = conn.execute(
        "SELECT rowid FROM vec_raw_item "
        "WHERE embedding MATCH ? ORDER BY distance LIMIT 1",
        (_make_vec(0.9, 0.1),)).fetchall()
    assert rows[0]["rowid"] == 1
