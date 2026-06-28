"""Task 2: view 生成同时产出 summary 与 view_text。"""
import asyncio
import json
from datetime import datetime, timezone
from src.db import init_db
from src.db.rows import StoryRow
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator


class FakeAI:
    async def complete(self, system, user):
        return json.dumps({
            "summary": "某公司宣布收购同业，待监管审批。",
            "view": "该交易可能影响行业竞争格局与相关方估值要素。"
        }, ensure_ascii=False)


def test_generate_item_returns_summary_and_view(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Acme buys Beta",
        first_seen_at=now, last_seen_at=now))
    gen = ViewGenerator(
        FakeAI(), ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
        ComplianceChecker())
    summary, view = asyncio.run(
        gen.generate_item(sid, "Acme buys Beta", "raw", ""))
    assert "收购" in summary
    assert "竞争格局" in view


def test_generate_item_view_still_works(tmp_path):
    """向后兼容：generate_item_view 仍返回 view 字符串。"""
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Sector news",
        first_seen_at=now, last_seen_at=now))
    gen = ViewGenerator(
        FakeAI(), ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
        ComplianceChecker())
    view = asyncio.run(gen.generate_item_view(
        sid, "Sector news", "raw summary", ""))
    assert "竞争格局" in view
