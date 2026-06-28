from src.db.rows import RawItemRow


def test_raw_item_row_roundtrip():
    row = RawItemRow(
        title="Acme acquires Beta", fetched_at="2026-06-28T00:00:00Z",
        dedup_key="k1", url="https://x.com/a",
    )
    assert row.id is None
    assert row.dedup_key == "k1"
    d = row.model_dump()
    assert d["title"] == "Acme acquires Beta"
