"""Task 2: ReviewQuery 跨期回顾测试。"""
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.entity_repo import EntityRepo, StoryEntityRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.rows import StoryRow, BriefRow, BriefItemRow, EntityRow
from src.review.queries import ReviewQuery


def _setup(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Acme buys Beta",
        first_seen_at=now, last_seen_at=now))
    StoryTagRepo(db).add(sid, TaxonomyRepo(db).get_id("product_group", "MA"))
    eid = EntityRepo(db).upsert(EntityRow(
        type="company", name="Acme", created_at=now))
    StoryEntityRepo(db).add(sid, eid, "primary")
    bid = BriefRepo(db).create(BriefRow(
        period_type="daily", period_date="2026-06-28", generated_at=now))
    BriefItemRepo(db).add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1,
        headline="Acme buys Beta", view_text="中性影响。", created_at=now))
    return db, eid


def test_by_taxonomy(tmp_path):
    db, _ = _setup(tmp_path)
    rows = ReviewQuery(db).by_taxonomy("product_group", "MA")
    assert rows and rows[0]["headline"] == "Acme buys Beta"


def test_by_entity(tmp_path):
    db, eid = _setup(tmp_path)
    rows = ReviewQuery(db).by_entity(eid)
    assert rows and rows[0]["headline"] == "Acme buys Beta"
