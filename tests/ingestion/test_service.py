"""Task 2: IngestionService 幂等落库 + 统计测试。"""
from datetime import datetime, timezone
from src.models import ContentItem, SourceType
from src.db import init_db
from src.db.repositories.raw_item_repo import RawItemRepo
from src.ingestion.service import IngestionService


def _ci(i):
    return ContentItem(
        id=f"rss:item:{i}", source_type=SourceType.RSS,
        title=f"news {i}", url=f"https://x.com/{i}", content="c",
        published_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
    )


def test_ingest_dedups_across_runs(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    svc = IngestionService(RawItemRepo(db))
    s1 = svc.ingest([_ci(1), _ci(2)])
    s2 = svc.ingest([_ci(1), _ci(2), _ci(3)])   # 1,2 重复
    assert s1.inserted == 2 and s1.skipped == 0
    assert s2.inserted == 1 and s2.skipped == 2
