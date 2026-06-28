from src.db.database import Database
from src.db.rows import RawItemRow
from src.db.repositories.raw_item_repo import RawItemRepo


def _repo(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    return RawItemRepo(db)


def _item(key):
    return RawItemRow(title="t", fetched_at="2026-06-28T00:00:00Z", dedup_key=key)


def test_upsert_inserts_new(tmp_path):
    repo = _repo(tmp_path)
    new_id, is_new = repo.upsert(_item("k1"))
    assert is_new is True
    assert new_id > 0


def test_upsert_is_idempotent_on_dedup_key(tmp_path):
    repo = _repo(tmp_path)
    id1, new1 = repo.upsert(_item("dup"))
    id2, new2 = repo.upsert(_item("dup"))
    assert new1 is True and new2 is False
    assert id1 == id2


def test_get_by_dedup_key(tmp_path):
    repo = _repo(tmp_path)
    repo.upsert(_item("k2"))
    got = repo.get_by_dedup_key("k2")
    assert got is not None and got.dedup_key == "k2"
