"""Task 1: BriefRenderer 测试。"""
import asyncio
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.rows import StoryRow, RawItemRow, BriefRow, BriefItemRow
from src.render.brief_renderer import BriefRenderer, DISCLAIMER


def test_render_contains_view_link_disclaimer(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    ri = RawItemRepo(db)
    rid, _ = ri.upsert(RawItemRow(
        title="Acme buys Beta", summary="s",
        url="https://x.com/a", fetched_at=now, dedup_key="k1"))
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Acme buys Beta",
        first_seen_at=now, last_seen_at=now))
    StoryMemberRepo(db).add(sid, rid, is_primary=True)
    bid = BriefRepo(db).create(BriefRow(
        period_type="daily", period_date="2026-06-28",
        generated_at=now, market_view_text="今日并购活动集中于 TMT。"))
    BriefItemRepo(db).add(BriefItemRow(
        brief_id=bid, story_id=sid, rank=1,
        headline="Acme buys Beta", summary="s",
        view_text="该交易可能影响行业竞争格局。", created_at=now))
    md = BriefRenderer(
        BriefRepo(db), BriefItemRepo(db), StoryRepo(db),
        StoryMemberRepo(db), RawItemRepo(db),
        StoryTagRepo(db), TaxonomyRepo(db)).render(bid)
    assert "Acme buys Beta" in md
    assert "https://x.com/a" in md          # 原文链接
    assert "竞争格局" in md                  # view
    assert DISCLAIMER in md                  # 免责声明
    assert "今日并购活动" in md               # 综合观点
