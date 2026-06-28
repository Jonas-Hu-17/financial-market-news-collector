"""组装当期 brief：选高分 story → 生成 view → 落库 + 综合观点。"""
from __future__ import annotations
from datetime import datetime, timezone
from ..db.rows import BriefRow, BriefItemRow


class BriefAssembler:
    def __init__(self, story_repo, score_repo, member_repo, raw_item_repo,
                 brief_repo, brief_item_repo, view_generator):
        self.stories = story_repo
        self.scores = score_repo
        self.members = member_repo
        self.raw = raw_item_repo
        self.briefs = brief_repo
        self.items = brief_item_repo
        self.view = view_generator

    async def build(self, period_type: str, period_date: str, *,
                    min_score: float = 6.0, max_items: int = 20,
                    language: str = "zh") -> int:
        now = datetime.now(timezone.utc).isoformat()
        scored = self._top_stories(min_score, max_items)
        brief_id = self.briefs.create(BriefRow(
            period_type=period_type, period_date=period_date, language=language,
            model="deepseek-v4-flash", generated_at=now, status="draft"))
        item_views = []
        for rank, (story_id, _score) in enumerate(scored, start=1):
            primary = self._primary_raw_item(story_id)
            title = primary.title if primary else ""
            summary = primary.summary if primary else ""
            summary, view = await self.view.generate_item(
                story_id, title, summary)
            item_views.append(view)
            self.items.add(BriefItemRow(
                brief_id=brief_id, story_id=story_id, rank=rank,
                headline=title, summary=summary, view_text=view,
                created_at=now))
        market_view = await self.view.generate_market_view(item_views)
        self.briefs.set_market_view(brief_id, market_view)
        return brief_id

    def _top_stories(self, min_score: float, max_items: int):
        ranked = []
        for s in self.stories.recent("0000"):
            sc = self.scores.latest_for_story(s.id)
            if sc and sc.score >= min_score:
                ranked.append((s.id, sc.score))
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked[:max_items]

    def _primary_raw_item(self, story_id: int):
        ids = self.members.raw_items_for_story(story_id)
        return self.raw.get(ids[0]) if ids else None
