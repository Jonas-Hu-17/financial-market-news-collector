from src.db.database import Database
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.seed_taxonomy import seed_taxonomy


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    return db


def test_seed_is_idempotent(tmp_path):
    db = _db(tmp_path)
    n1 = seed_taxonomy(db)
    n2 = seed_taxonomy(db)
    repo = TaxonomyRepo(db)
    market = repo.list_by_dimension("market_type")
    assert n1 > 0
    assert {m.code for m in market} == {"primary", "secondary"}
    # 再次 seed 不应重复增加
    assert len(repo.list_by_dimension("market_type")) == 2


def test_get_id(tmp_path):
    db = _db(tmp_path)
    seed_taxonomy(db)
    repo = TaxonomyRepo(db)
    assert repo.get_id("industry_group", "TMT") is not None
