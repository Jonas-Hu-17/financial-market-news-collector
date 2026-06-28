"""Task 1: ContentItem → RawItemRow 映射测试（含 dedup_key）。"""
from datetime import datetime, timezone
from src.models import ContentItem, SourceType
from src.ingestion.mapper import canonicalize_url, content_hash, to_raw_item


def _ci(url, title="Acme acquires Beta"):
    return ContentItem(
        id="rss:item:1", source_type=SourceType.RSS, title=title, url=url,
        content="summary text", published_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
    )


def test_canonicalize_strips_utm_and_fragment():
    a = canonicalize_url("https://X.com/a?utm_source=x&id=5#frag")
    b = canonicalize_url("https://x.com/a?id=5")
    assert a == b


def test_same_event_same_dedup_key():
    r1 = to_raw_item(_ci("https://x.com/a?utm_source=tw"), source_id=1)
    r2 = to_raw_item(_ci("https://x.com/a"), source_id=2)
    assert r1.dedup_key == r2.dedup_key   # 跨源同一文章 → 同 key


def test_different_title_different_key():
    r1 = to_raw_item(_ci("https://x.com/a", "title one"), 1)
    r2 = to_raw_item(_ci("https://x.com/b", "title two"), 1)
    assert r1.dedup_key != r2.dedup_key
