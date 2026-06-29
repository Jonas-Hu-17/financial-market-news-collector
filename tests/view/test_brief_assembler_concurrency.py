"""Task B: 测试 view 生成并发化 — BriefAssembler.build 并发生成各条 view。"""
import asyncio
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.analysis_repo import ScoreRepo, StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.rows import StoryRow, RawItemRow, ScoreRow
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator
from src.view.brief_assembler import BriefAssembler


class FakeAIForConcurrency:
    def __init__(self, n):
        self.active = 0
        self.max_concurrent = 0
        self.n = n

    async def complete(self, system, user):
        self.active += 1
        self.max_concurrent = max(self.max_concurrent, self.active)
        await asyncio.sleep(0.03)  # allow overlap
        self.active -= 1
        return "该事件可能影响相关市场估值。"


def test_view_generation_runs_concurrently(tmp_path):
    """验证 BriefAssembler.build 为多条 story 并发生成 item view。"""
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    n = 5

    ri = RawItemRepo(db)
    sr = StoryRepo(db)
    sm = StoryMemberRepo(db)
    sc = ScoreRepo(db)
    tax = TaxonomyRepo(db)
    st = StoryTagRepo(db)

    for i in range(n):
        rid, _ = ri.upsert(RawItemRow(
            title=f"Headline {i}", summary=f"summary {i}",
            fetched_at=now, dedup_key=f"k{i}"))
        sid = sr.create(StoryRow(
            canonical_title=f"Headline {i}",
            first_seen_at=now, last_seen_at=now))
        sm.add(sid, rid, is_primary=True)
        sc.add(ScoreRow(story_id=sid, model="deepseek-v4-flash",
                         score=8.0, importance_rationale="important",
                         scored_at=now))
        # 必须有标签
        st.add(sid, tax.get_id("product_group", "MA"))

    fake_ai = FakeAIForConcurrency(n)
    gen = ViewGenerator(fake_ai,
                        ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)),
                        ComplianceChecker())
    asm = BriefAssembler(sr, ScoreRepo(db), sm, RawItemRepo(db),
                         BriefRepo(db), BriefItemRepo(db), gen)

    bid = asyncio.run(asm.build("daily", "2026-06-28",
                                 min_score=5.0, max_items=20))
    assert bid > 0

    items = BriefItemRepo(db).list_for_brief(bid)
    assert len(items) == n

    # 核心断言：当前顺序循环下 max_concurrent=1，并发实现后应 > 1
    assert fake_ai.max_concurrent > 1, (
        f"Expected concurrent view generation but "
        f"max_concurrent={fake_ai.max_concurrent}. "
        "View generation loop appears sequential."
    )
