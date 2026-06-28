"""把 brief 渲染为 Markdown（纯读 DB，不调 LLM）。"""
from __future__ import annotations

DISCLAIMER = (
    "> 免责声明：本内容为公开信息汇总与中性影响陈述，不构成任何投资建议、"
    "买卖推荐或目标价。请自行核实并独立决策。"
)


class BriefRenderer:
    def __init__(self, brief_repo, brief_item_repo, story_repo, member_repo,
                 raw_item_repo, story_tag_repo, taxonomy_repo):
        self.briefs = brief_repo
        self.items = brief_item_repo
        self.stories = story_repo
        self.members = member_repo
        self.raw = raw_item_repo
        self.tags = story_tag_repo
        self.tax = taxonomy_repo

    def render(self, brief_id: int) -> str:
        brief = self.briefs.get(brief_id)
        items = self.items.list_for_brief(brief_id)
        lines = [
            f"# 金融市场 Brief — {brief.period_date}（{brief.period_type}）",
            "",
        ]
        if brief.market_view_text:
            lines += ["## 综合市场观点", brief.market_view_text, ""]
        lines += ["## 今日要闻", ""]
        for it in sorted(items, key=lambda x: x.rank):
            url = self._primary_url(it.story_id)
            link = f"（[原文]({url})）" if url else ""
            lines += [f"### {it.rank}. {it.headline} {link}"]
            if it.summary:
                lines += [f"_{it.summary}_", ""]
            lines += [f"**影响（中性）**：{it.view_text}", ""]
        lines += ["---", DISCLAIMER]
        return "\n".join(lines)

    def _primary_url(self, story_id: int):
        ids = self.members.raw_items_for_story(story_id)
        if not ids:
            return None
        item = self.raw.get(ids[0])
        return item.url if item else None
