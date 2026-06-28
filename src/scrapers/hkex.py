"""HKEX 披露易公告抓取器。"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List
from .base import BaseScraper
from ..models import ContentItem, SourceType


def parse_hkex_json(data: dict) -> List[ContentItem]:
    out: List[ContentItem] = []
    for n in data.get("newslist", []):
        try:
            published = datetime.strptime(n["DATE_TIME"], "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc)
        except Exception:
            published = datetime.now(timezone.utc)
        out.append(ContentItem(
            id=f"hkex:{n.get('NEWS_ID')}", source_type=SourceType.RSS,
            title=f"[{n.get('STOCK_CODE', '')}] {n.get('TITLE', '')}".strip(),
            url=n.get("FILE_LINK"), content=n.get("TITLE", ""),
            published_at=published,
        ))
    return out


class HKEXScraper(BaseScraper):
    async def fetch(self, since: datetime) -> List[ContentItem]:
        url = self.config.get("endpoint")
        if not url:
            return []
        try:
            resp = await self.client.get(url, timeout=30)
            return [i for i in parse_hkex_json(resp.json()) if i.published_at >= since]
        except Exception:
            return []
