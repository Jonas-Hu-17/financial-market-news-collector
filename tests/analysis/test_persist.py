"""Task 3: AnalysisPersister 测试。"""
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import ScoreRepo, StoryTagRepo
from src.db.repositories.entity_repo import EntityRepo, StoryEntityRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.rows import StoryRow, EntityRow
from src.analysis.financial_analyzer import AnalysisResult
from src.analysis.persist import AnalysisPersister


def test_persist_writes_all(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(
        canonical_title="Acme buys Beta",
        first_seen_at=now, last_seen_at=now))

    p = AnalysisPersister(
        ScoreRepo(db), StoryTagRepo(db), EntityRepo(db),
        StoryEntityRepo(db), TaxonomyRepo(db), model_name="deepseek-chat")

    res = AnalysisResult(8.0, "big deal",
        {"market_type": "secondary", "industry_group": "TMT",
         "product_group": "MA", "region": "GreaterChina",
         "asset_class": "Equity"},
        [{"type": "company", "name": "Acme", "ticker": None, "role": "primary"}])

    p.persist(sid, res)

    # 分写入
    assert ScoreRepo(db).latest_for_story(sid).score == 8.0
    # 5 个维度标签全部写入
    assert len(StoryTagRepo(db).taxonomy_ids_for_story(sid)) == 5
    # 实体写入并关联到 story
    eid = EntityRepo(db).upsert(EntityRow(
        type="company", name="Acme", created_at=now))
    assert StoryEntityRepo(db).stories_for_entity(eid) == [sid]
