"""Task C: 降低抓取超时 + 并发抓取 — 测试与回归保护。"""
import asyncio
from datetime import datetime, timezone
from src.db import init_db
from src.models import ContentItem, SourceType
from src.marketnews_orchestrator import MarketNewsOrchestrator


class FakeScraper:
    """使用共享 counter 记录跨 scraper 的并发度。"""
    def __init__(self, items, counter, delay=0.08):
        self.items = items
        self.counter = counter
        self.delay = delay

    async def fetch(self, since):
        self.counter["active"] += 1
        self.counter["max"] = max(self.counter["max"], self.counter["active"])
        await asyncio.sleep(self.delay)
        self.counter["active"] -= 1
        return self.items


class MinimalFakeAI:
    async def complete(self, system, user):
        return '{"score":8.0,"rationale":"ok","tags":{},"entities":[]}'


def test_fetch_runs_concurrently(tmp_path, monkeypatch):
    """验证 orchestrator 第1步并发抓取多个 scraper（非顺序）。"""
    db = init_db(str(tmp_path / "t.db"))

    # 避免下载 sentence-transformers
    from src.embedding.service import EmbeddingService

    def fake_embed(_self, texts):
        import hashlib
        out = []
        for t in texts:
            h = int(hashlib.md5(t.encode()).hexdigest()[:8], 16)
            out.append([float((h >> (i % 16)) & 1) for i in range(384)])
        return out

    def fake_embed_one(_self, text):
        return fake_embed(_self, [text])[0]

    monkeypatch.setattr(EmbeddingService, "embed", fake_embed)
    monkeypatch.setattr(EmbeddingService, "embed_one", fake_embed_one)

    counter = {"active": 0, "max": 0}
    n_scrapers = 3
    scrapers = [FakeScraper(
        [ContentItem(
            id=f"rss:{i}:{j}", source_type=SourceType.RSS,
            title=f"Item {i}-{j}", url=f"https://example.com/a{i}{j}",
            content="", published_at=datetime.now(timezone.utc),
        ) for j in range(2)],
        counter=counter,
        delay=0.1,
    ) for i in range(n_scrapers)]

    orch = MarketNewsOrchestrator(config={}, db=db, ai_client=MinimalFakeAI())
    orch._scrapers = scrapers

    brief_id = asyncio.run(orch.run(period_type="daily"))
    assert brief_id > 0

    # 核心断言：顺序循环下 max=1，asyncio.gather 并发后 >1
    assert counter["max"] > 1, (
        f"Expected concurrent fetch across scrapers but "
        f"max_concurrent={counter['max']}. Fetch appears sequential."
    )
