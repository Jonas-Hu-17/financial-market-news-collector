"""Task 5: 模板渲染验证（Cartesian 视觉 + 内容结构）。"""
import pytest
from fastapi.testclient import TestClient
from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.rows import (
    BriefRow, BriefItemRow, StoryRow, RawItemRow, TaxonomyRow)
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.web.app import create_app


def _seed_brief_with_tags(db):
    now = "2026-06-28T00:00:00Z"
    ri, _ = RawItemRepo(db).upsert(RawItemRow(
        title="Test headline", summary="Raw summary",
        url="https://example.com/test", dedup_key="dk:test2",
        fetched_at=now, published_at=now))
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Test headline", first_seen_at=now,
        last_seen_at=now))
    StoryMemberRepo(db).add(sid, ri, is_primary=True)
    tax_id = TaxonomyRepo(db).upsert(TaxonomyRow(
        dimension="industry_group", code="tech", label="科技"))
    StoryTagRepo(db).add(sid, tax_id)
    br = BriefRepo(db)
    bid = br.create(BriefRow(
        period_type="daily", period_date="2026-06-28", language="zh",
        model="deepseek-chat", generated_at=now, status="draft",
        market_view_text="综合市场观点文本"))
    bir = BriefItemRepo(db)
    bir.add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1,
        headline="Test headline", summary="AI 摘要测试",
        view_text="中性影响陈述测试", created_at=now))
    return "2026-06-28"


@pytest.fixture
def template_client(tmp_path):
    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    _seed_brief_with_tags(db)
    app = create_app(db_path)
    return TestClient(app)


def test_template_has_title(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert r.status_code == 200
    assert "Financial Market News Collector" in r.text


def test_template_has_neutral_impact_label(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "影响（中性）" in r.text


def test_template_has_disclaimer(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "免责声明" in r.text


def test_template_has_original_link(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "原文" in r.text or "example.com" in r.text


def test_template_has_filter_chips(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "全部" in r.text
    assert "科技" in r.text


def test_template_has_history_nav(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "历史" in r.text or "/brief/" in r.text


def test_template_has_market_view(template_client):
    r = template_client.get("/brief/2026-06-28")
    assert "综合市场观点" in r.text
