"""SEC EDGAR 抓取器：8-K（重大事件/并购）与 Form D（私募融资）。"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List
import feedparser
from .base import BaseScraper
from ..models import ContentItem, SourceType

_FEEDS = {
    "8-K": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&output=atom&count=100",
    "D":   "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=D&output=atom&count=100",
}


def parse_edgar_atom(xml: str, form_type: str) -> List[ContentItem]:
    feed = feedparser.parse(xml)
    out: List[ContentItem] = []
    for e in feed.entries:
        link = e.get("link") or (e.links[0].href if e.get("links") else "")
        pub = e.get("updated") or e.get("published")
        try:
            published = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            published = datetime.now(timezone.utc)
        out.append(ContentItem(
            id=f"edgar:{form_type}:{link}", source_type=SourceType.RSS,
            title=e.get("title", f"{form_type} filing"), url=link,
            content=e.get("summary", ""), published_at=published,
        ))
    return out


class SECEdgarScraper(BaseScraper):
    async def fetch(self, since: datetime) -> List[ContentItem]:
        items: List[ContentItem] = []
        headers = {"User-Agent": self.config.get(
            "user_agent", "MarketNews research contact@example.com")}
        for form_type in self.config.get("forms", ["8-K", "D"]):
            try:
                resp = await self.client.get(_FEEDS[form_type], headers=headers, timeout=30)
                items.extend([i for i in parse_edgar_atom(resp.text, form_type)
                              if i.published_at >= since])
            except Exception:
                continue   # 单源失败跳过，不中断
        return items
