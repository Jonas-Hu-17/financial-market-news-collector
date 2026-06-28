from src.db import Database, init_db


def test_init_db(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    assert isinstance(db, Database)
    conn = db.connect()
    n = conn.execute("SELECT COUNT(*) FROM taxonomy").fetchone()[0]
    assert n > 0
