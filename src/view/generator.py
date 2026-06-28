"""中性 view 生成：路由选模板 → 调模型 → 合规扫描/重写。"""
from __future__ import annotations
import json
import re
from .view_templates import (NEUTRAL_SYSTEM, TEMPLATES, MARKET_VIEW_SYSTEM,
                             build_market_view_user)

_REWRITE_HINT = ("\n\nIMPORTANT: Your previous answer contained advisory or directional "
                 "language. Rewrite it as a strictly neutral impact statement: no "
                 "buy/sell/hold, no rating, no price target, no bullish/bearish stance.")


class ViewGenerator:
    def __init__(self, ai_client, router, compliance):
        self.ai = ai_client
        self.router = router
        self.compliance = compliance

    async def generate_item(self, story_id: int, title: str,
                            summary: str, context: str = "") -> tuple[str, str]:
        """返回 (summary, view_text)。summary 为客观一句话，view 为中性影响陈述。"""
        key = self.router.route(story_id)
        user = TEMPLATES[key].format(title=title, summary=summary or "(none)",
                                     context=context or "(none)")
        raw = await self.ai.complete(NEUTRAL_SYSTEM, user)
        try:
            data = json.loads(_strip_fences(raw))
            ai_summary = data.get("summary", "")
            ai_view = data.get("view", "")
        except Exception:
            ai_summary, ai_view = "", raw
        # 合规扫描 view
        if not self.compliance.is_clean(ai_view):
            view2 = await self.ai.complete(NEUTRAL_SYSTEM, user + _REWRITE_HINT)
            if self.compliance.is_clean(view2):
                ai_view = view2.strip()
            else:
                ai_view = _strip_violating_sentences(view2, self.compliance)
        # 合规扫描 summary
        if not self.compliance.is_clean(ai_summary):
            ai_summary = _strip_violating_sentences(ai_summary, self.compliance)
        return ai_summary.strip(), ai_view.strip()

    async def generate_item_view(self, story_id: int, title: str,
                                 summary: str, context: str = "") -> str:
        """兼容旧接口：只返回 view 文本。"""
        _, view = await self.generate_item(story_id, title, summary, context)
        return view

    async def generate_market_view(self, item_views: list[str]) -> str:
        if not item_views:
            return ""
        text = await self.ai.complete(
            MARKET_VIEW_SYSTEM, build_market_view_user(item_views))
        if self.compliance.is_clean(text):
            return text.strip()
        return _strip_violating_sentences(text, self.compliance)


def _strip_fences(text: str) -> str:
    """移除 Markdown 代码块标记。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def _strip_violating_sentences(text: str, compliance) -> str:
    parts = re.split(r"(?<=[。.!?])\s*", text)
    kept = [p for p in parts if p and compliance.is_clean(p)]
    return " ".join(kept).strip() or "（本条因合规过滤暂无中性观点）"
