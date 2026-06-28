"""Task 3: MarketNewsOrchestrator 集成测试（假源/假 AI，端到端不触网）。"""
import asyncio
import json
from datetime import datetime, timezone
from src.db import init_db
from src.models import ContentItem, SourceType
from src.marketnews_orchestrator import MarketNewsOrchestrator


class FakeScraper:
    def __init__(self, items):
        self.items = items

    async def fetch(self, since):
        return self.items


class FakeAI:
    async def complete(self, system, user):
        if "Score each item" in system:   # 打分调用
            return json.dumps({
                "score": 8.0,
                "rationale": "big deal",
                "tags": {
                    "market_type": "secondary", "industry_group": "TMT",
                    "product_group": "MA", "region": "GreaterChina",
                    "asset_class": "Equity",
                },
                "entities": [
                    {"type": "company", "name": "Acme", "ticker": None,
                     "role": "primary"},
                ],
            })
        # view 调用
        return "该交易可能影响行业竞争格局与相关方估值要素。"


def test_end_to_end_produces_brief(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    items = [
        ContentItem(
            id="rss:i:1", source_type=SourceType.RSS,
            title="Acme buys Beta", url="https://x.com/a",
            content="deal", published_at=datetime.now(timezone.utc))
    ]
    orch = MarketNewsOrchestrator(config={}, db=db, ai_client=FakeAI())
    orch._scrapers = [FakeScraper(items)]  # 注入假源
    brief_id = asyncio.run(orch.run(period_type="daily"))
    assert brief_id > 0

    from src.db.repositories.brief_repo import BriefItemRepo
    items_out = BriefItemRepo(db).list_for_brief(brief_id)
    assert len(items_out) >= 1
