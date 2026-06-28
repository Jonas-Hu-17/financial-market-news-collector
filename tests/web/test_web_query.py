"""Task 3: WebQuery 测试。"""
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.rows import (
    BriefRow, BriefItemRow, StoryRow, RawItemRow, TaxonomyRow, ScoreRow)
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.analysis_repo import StoryTagRepo, ScoreRepo
from src.db.repositories.feedback_repo import FeedbackRepo


def _seed_full_brief(db) -> int:
    """建完整一期 brief 及其关联数据，返回 brief 的 date（字符串）。"""
    now = "2026-06-28T00:00:00Z"

    # raw_item
    ri, _ = RawItemRepo(db).upsert(RawItemRow(
        title="News headline", summary="Raw summary",
        url="https://example.com/news",
        dedup_key="dk:1", fetched_at=now, published_at=now))

    # story
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="News headline", first_seen_at=now, last_seen_at=now))
    StoryMemberRepo(db).add(sid, ri, is_primary=True)

    # taxonomy + tag
    tax_id = TaxonomyRepo(db).upsert(TaxonomyRow(
        dimension="industry_group", code="tech", label="科技"))

    # Need a tax row with dimension="product_group" for route test too
    tax_id2 = TaxonomyRepo(db).upsert(TaxonomyRow(
        dimension="product_group", code="ai", label="AI"))
    StoryTagRepo(db).add(sid, tax_id)
    StoryTagRepo(db).add(sid, tax_id2)

    # score
    ScoreRepo(db).add(ScoreRow(
        story_id=sid, model="deepseek-chat", score=8.0,
        importance_rationale="important", scored_at=now))

    # brief
    bid = BriefRepo(db).create(BriefRow(
        period_type="daily", period_date="2026-06-28", language="zh",
        model="deepseek-chat", generated_at=now, status="draft",
        market_view_text="综合市场观点文本"))

    # brief_item
    bir = BriefItemRepo(db)
    bir.add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1,
        headline="News headline", summary="AI 概括摘要",
        view_text="中性影响陈述", created_at=now))

    # feedback
    ensure_web_columns(db)
    fr = FeedbackRepo(db)
    # Need the brief_item id — re-query it
    import sqlite3
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id FROM brief_item WHERE brief_id=? AND rank=1",
            (bid,)).fetchone()
        bi_id = row["id"]
    finally:
        conn.close()
    fr.upsert_rating(brief_item_id=bi_id, rating="up", anon_id="a1")
    fr.upsert_rating(brief_item_id=bi_id, rating="up", anon_id="a2")
    fr.upsert_rating(brief_item_id=bi_id, rating="down", anon_id="a3")

    return "2026-06-28"


def test_web_query_latest_date(tmp_path):
    from src.web.queries import WebQuery

    db = init_db(str(tmp_path / "t.db"))
    _seed_full_brief(db)
    q = WebQuery(db)
    assert q.latest_date() == "2026-06-28"


def test_web_query_list_dates(tmp_path):
    from src.web.queries import WebQuery

    db = init_db(str(tmp_path / "t.db"))
    _seed_full_brief(db)
    q = WebQuery(db)
    dates = q.list_dates()
    assert "2026-06-28" in dates


def test_brief_for_web(tmp_path):
    from src.web.queries import WebQuery

    db = init_db(str(tmp_path / "t.db"))
    _seed_full_brief(db)
    q = WebQuery(db)
    data = q.brief_for_web("2026-06-28")
    assert data is not None
    assert data["date"] == "2026-06-28"
    assert "综合市场观点" in data["market_view"]
    assert len(data["items"]) == 1
    it = data["items"][0]
    assert it["headline"] == "News headline"
    assert "AI 概括" in it["summary"]
    assert "中性影响" in it["view"]
    assert it["url"] == "https://example.com/news"
    assert len(it["tags"]) == 2
    assert it["up"] == 2
    assert it["down"] == 1
    # 应有 tagcodes 用于筛选
    assert it["tagcodes"] is not None
