"""中性 view 生成：路由选模板 → 调模型 → 合规扫描/重写。"""
from __future__ import annotations
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

    async def generate_item_view(self, story_id: int, title: str,
                                 summary: str, context: str = "") -> str:
        key = self.router.route(story_id)
        user = TEMPLATES[key].format(title=title, summary=summary or "(none)",
                                     context=context or "(none)")
        text = await self.ai.complete(NEUTRAL_SYSTEM, user)
        if self.compliance.is_clean(text):
            return text.strip()
        text2 = await self.ai.complete(NEUTRAL_SYSTEM, user + _REWRITE_HINT)
        if self.compliance.is_clean(text2):
            return text2.strip()
        return _strip_violating_sentences(text2, self.compliance)

    async def generate_market_view(self, item_views: list[str]) -> str:
        if not item_views:
            return ""
        text = await self.ai.complete(
            MARKET_VIEW_SYSTEM, build_market_view_user(item_views))
        if self.compliance.is_clean(text):
            return text.strip()
        return _strip_violating_sentences(text, self.compliance)


def _strip_violating_sentences(text: str, compliance) -> str:
    parts = re.split(r"(?<=[。.!?])\s*", text)
    kept = [p for p in parts if p and compliance.is_clean(p)]
    return " ".join(kept).strip() or "（本条因合规过滤暂无中性观点）"
