"""Task 2: ViewRouter 按标签选模板测试。"""
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.rows import StoryRow
from src.view.router import ViewRouter


def _story_with_tags(db, codes):
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(
        StoryRow(canonical_title="x", first_seen_at=now, last_seen_at=now))
    tax, st = TaxonomyRepo(db), StoryTagRepo(db)
    for dim, code in codes.items():
        st.add(sid, tax.get_id(dim, code))
    return sid


def test_routes_ma(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    sid = _story_with_tags(db, {"product_group": "MA"})
    assert ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)).route(sid) == "ma"


def test_routes_primary_market(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    sid = _story_with_tags(db, {"product_group": "VC", "market_type": "primary"})
    assert ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)).route(sid) == "primary_market"
