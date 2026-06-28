"""Task 4a: ViewGenerator 测试（假 AI + 合规扫描）。"""
import asyncio
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.rows import StoryRow
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator


class FakeAI:
    def __init__(self, seq):
        self.seq = list(seq)
        self.calls = []

    async def complete(self, system, user):
        self.calls.append((system, user))
        return self.seq.pop(0)


def test_generate_item_view_clean(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(
        StoryRow(canonical_title="x", first_seen_at=now, last_seen_at=now))
    gen = ViewGenerator(
        FakeAI(["该交易可能影响行业竞争格局。"]),
        ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
        ComplianceChecker(),
    )
    out = asyncio.run(gen.generate_item_view(sid, "Acme buys Beta", "deal"))
    assert "竞争格局" in out


def test_generate_item_view_rewrites_on_violation(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(
        StoryRow(canonical_title="x", first_seen_at=now, last_seen_at=now))
    # 第一次返回含违规措辞，第二次返回干净
    gen = ViewGenerator(
        FakeAI(["建议买入该股票。", "该消息可能影响相关方估值要素。"]),
        ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
        ComplianceChecker(),
    )
    out = asyncio.run(gen.generate_item_view(sid, "x", "y"))
    assert "建议买入" not in out
