"""Task 1: anon_id migration + EventRepo + FeedbackRepo 测试。"""
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.repositories.feedback_repo import EventRepo, FeedbackRepo


def _db(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    ensure_web_columns(db)
    return db


def _seed_brief_item(db):
    """插入 brief、story 和 brief_item 以满足 FK 约束。"""
    from src.db.rows import BriefRow, BriefItemRow, StoryRow
    from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
    from src.db.repositories.story_repo import StoryRepo
    # 需要先建 story（brief_item 引用 story.id）
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="test story", first_seen_at="2026-06-28T00:00:00Z",
        last_seen_at="2026-06-28T00:00:00Z"))
    br = BriefRepo(db)
    bir = BriefItemRepo(db)
    bid = br.create(BriefRow(
        period_type="daily", period_date="2026-06-28", language="zh",
        model="test", generated_at="2026-06-28T00:00:00Z", status="draft"))
    iid = bir.add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1, headline="test",
        created_at="2026-06-28T00:00:00Z"))
    return iid


def test_migration_idempotent(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    ensure_web_columns(db)
    ensure_web_columns(db)  # 跑两次不报错
    conn = db.connect()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(feedback)")}
    assert "anon_id" in cols
    conn.close()


def test_event_add(tmp_path):
    db = _db(tmp_path)
    bid = _seed_brief_item(db)
    eid = EventRepo(db).add(brief_item_id=bid, type="click", anon_id="a1")
    assert eid > 0


def test_feedback_counts_and_one_vote(tmp_path):
    db = _db(tmp_path)
    bid = _seed_brief_item(db)
    fr = FeedbackRepo(db)
    fr.upsert_rating(brief_item_id=bid, rating="up", anon_id="a1")
    fr.upsert_rating(brief_item_id=bid, rating="up", anon_id="a2")
    fr.upsert_rating(brief_item_id=bid, rating="down", anon_id="a1")  # a1 改投
    c = fr.counts(bid)
    assert c == {"up": 1, "down": 1}
