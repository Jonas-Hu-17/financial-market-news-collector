"""Task A: 测试打分并发化 — MarketNewsOrchestrator 第4步并发执行。"""
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


class FakeAIClient:
    def __init__(self, counter: dict | None = None):
        self.active = 0
        self.max_concurrent = 0
        self.counter = counter  # shared dict for cross-task tracking

    async def complete(self, system, user):
        self.active += 1
        if self.counter is not None:
            self.counter["active"] += 1
            self.counter["max"] = max(self.counter.get("max", 0),
                                      self.counter["active"])
        self.max_concurrent = max(self.max_concurrent, self.active)
        await asyncio.sleep(0.03)  # small delay to allow overlap
        self.active -= 1
        if self.counter is not None:
            self.counter["active"] -= 1
        if "Score each item" in system:
            return json.dumps({
                "score": 8.0,
                "rationale": "big deal",
                "tags": {"market_type": "secondary", "industry_group": "TMT",
                         "product_group": "MA", "region": "GreaterChina",
                         "asset_class": "Equity"},
                "entities": [
                    {"type": "company", "name": "Acme", "ticker": None,
                     "role": "primary"},
                ],
            })
        # view 调用
        return "该交易可能影响行业竞争格局与相关方估值要素。"


def test_scoring_runs_concurrently(tmp_path, monkeypatch):
    """验证 orchestrator 第4步为多个 story 并发生成分析（非顺序）。"""
    db = init_db(str(tmp_path / "t.db"))
    n = 6  # enough items to saturate default concurrency
    items = [
        ContentItem(
            id=f"rss:i:{i}", source_type=SourceType.RSS,
            title=f"Unique headline number {i}",
            url=f"https://example.com/a{i}",
            content="financial news",
            published_at=datetime.now(timezone.utc),
        )
        for i in range(n)
    ]

    # 避免下载 sentence-transformers：每篇 news 用唯一向量确保不聚类
    from src.embedding.service import EmbeddingService

    def fake_embed_one(_self, text: str) -> list[float]:
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # 384-dim near-orthogonal vector
        return [float((h >> (i % 16)) & 1) for i in range(384)]

    def fake_embed(_self, texts: list[str]) -> list[list[float]]:
        return [fake_embed_one(_self, t) for t in texts]

    monkeypatch.setattr(EmbeddingService, "embed_one", fake_embed_one)
    monkeypatch.setattr(EmbeddingService, "embed", fake_embed)

    counter: dict = {"active": 0, "max": 0}
    fake_ai = FakeAIClient(counter=counter)
    orch = MarketNewsOrchestrator(config={}, db=db, ai_client=fake_ai)
    orch._scrapers = [FakeScraper(items)]

    brief_id = asyncio.run(orch.run(period_type="daily"))
    assert brief_id > 0

    # 核心断言：当前顺序循环下 max 应=1，并发实现后应>1
    assert counter["max"] > 1, (
        f"Expected concurrent scoring but max_active={counter['max']}. "
        "Scoring loop appears sequential."
    )
