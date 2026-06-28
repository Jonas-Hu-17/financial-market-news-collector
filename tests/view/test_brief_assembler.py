"""Task 4b: BriefAssembler 测试（假 AI）。"""
import asyncio
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.analysis_repo import ScoreRepo, StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.rows import StoryRow, RawItemRow, ScoreRow
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator
from src.view.brief_assembler import BriefAssembler


class FakeAI:
    def __init__(self, seq):
        self.seq = list(seq)
        self.calls = []

    async def complete(self, system, user):
        self.calls.append((system, user))
        return self.seq.pop(0)


def test_brief_assembler_builds_brief(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()

    # 创建 story + raw_item + score
    ri = RawItemRepo(db)
    rid, _ = ri.upsert(RawItemRow(
        title="Acme buys Beta", summary="big deal",
        fetched_at=now, dedup_key="k1"))

    sr = StoryRepo(db)
    sid = sr.create(StoryRow(
        canonical_title="Acme buys Beta",
        first_seen_at=now, last_seen_at=now))

    # 给 story 关联 raw_item
    from src.db.repositories.story_repo import StoryMemberRepo
    StoryMemberRepo(db).add(sid, rid, is_primary=True)

    # 打分
    ScoreRepo(db).add(ScoreRow(
        story_id=sid, model="deepseek-chat", score=8.0,
        importance_rationale="big M&A", scored_at=now))

    # 给 story 加标签（有 MA 才能路由到模板）
    tax = TaxonomyRepo(db)
    st = StoryTagRepo(db)
    st.add(sid, tax.get_id("product_group", "MA"))

    # 假 AI：item view + market view 各一次调用
    fake = FakeAI([
        "该并购交易可能改变行业竞争格局。",
        "今日市场以并购活动为主。",
    ])

    gen = ViewGenerator(fake, ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
                        ComplianceChecker())
    asm = BriefAssembler(sr, ScoreRepo(db), StoryMemberRepo(db),
                         RawItemRepo(db), BriefRepo(db),
                         BriefItemRepo(db), gen)

    bid = asyncio.run(asm.build("daily", "2026-06-28", min_score=5.0, max_items=20))
    assert bid > 0

    # 验证 brief 落库
    brief = BriefRepo(db).get(bid)
    assert brief is not None
    assert brief.period_type == "daily"

    # 验证 brief_item
    items = BriefItemRepo(db).list_for_brief(bid)
    assert len(items) == 1
    assert items[0].story_id == sid
    assert "竞争格局" in items[0].view_text
