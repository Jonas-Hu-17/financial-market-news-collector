"""ContentItem → RawItemRow 映射，计算规范 URL、内容哈希与全局 dedup_key。"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from src.models import ContentItem
from src.db.rows import RawItemRow

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_")


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    query = [(k, v) for k, v in parse_qsl(parts.query)
             if not k.lower().startswith(_TRACKING_PREFIXES)]
    query.sort()
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def content_hash(title: str, summary: Optional[str]) -> str:
    base = (title or "").strip() + "\n" + (summary or "").strip()
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def to_raw_item(item: ContentItem, source_id: Optional[int]) -> RawItemRow:
    canon = canonicalize_url(str(item.url))
    chash = content_hash(item.title, item.content)
    dedup = hashlib.sha256(f"{canon}|{chash}".encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    return RawItemRow(
        source_id=source_id,
        external_id=item.id,
        url=str(item.url),
        canonical_url=canon,
        title=item.title,
        summary=item.content,
        author=item.author,
        published_at=item.published_at.isoformat() if item.published_at else None,
        fetched_at=now,
        dedup_key=dedup,
        content_hash=chash,
        language=None,
        raw_payload=item.model_dump_json(),
    )
