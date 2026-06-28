"""Task 4: FastAPI 应用 + 页面与 API 接口测试。"""
from fastapi.testclient import TestClient
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.rows import (
    BriefRow, BriefItemRow, StoryRow, RawItemRow)
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.web.app import create_app


def _seed_brief(db):
    """建一期 brief + 1 条 brief_item 供页面渲染。"""
    now = "2026-06-28T00:00:00Z"
    ri, _ = RawItemRepo(db).upsert(RawItemRow(
        title="Test headline", summary="Raw summary",
        url="https://example.com/test", dedup_key="dk:test",
        fetched_at=now, published_at=now))
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Test headline", first_seen_at=now,
        last_seen_at=now))
    StoryMemberRepo(db).add(sid, ri, is_primary=True)
    br = BriefRepo(db)
    bid = br.create(BriefRow(
        period_type="daily", period_date="2026-06-28", language="zh",
        model="deepseek-v4-flash", generated_at=now, status="draft",
        market_view_text="综合市场观点文本"))
    bir = BriefItemRepo(db)
    bir.add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1,
        headline="Test headline", summary="AI 摘要测试",
        view_text="中性影响陈述测试", created_at=now))


def test_feedback_endpoint(tmp_path):
    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    ensure_web_columns(db)
    _seed_brief(db)
    app = create_app(db_path)
    client = TestClient(app)
    r = client.post("/api/feedback", json={
        "brief_item_id": 1, "rating": "up", "anon_id": "a1"})
    assert r.status_code == 200
    data = r.json()
    assert data["up"] == 1


def test_event_endpoint(tmp_path):
    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    ensure_web_columns(db)
    _seed_brief(db)
    app = create_app(db_path)
    client = TestClient(app)
    r = client.post("/api/event", json={
        "brief_item_id": 1, "type": "click", "anon_id": "a1"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_index_renders(tmp_path):
    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    _seed_brief(db)
    app = create_app(db_path)
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Financial Market News Collector" in r.text


def test_brief_page_renders(tmp_path):
    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    _seed_brief(db)
    app = create_app(db_path)
    client = TestClient(app)
    r = client.get("/brief/2026-06-28")
    assert r.status_code == 200
    assert "Test headline" in r.text
    assert "AI 摘要测试" in r.text
    assert "中性影响陈述测试" in r.text


def test_empty_database(tmp_path):
    """无 brief 时返回空态页面，不报 500。"""
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    app = create_app(db_path)
    client = TestClient(app)
    r = client.get("/brief/2099-01-01")
    assert r.status_code == 200
    assert "暂无" in r.text or "brief" in r.text.lower()
