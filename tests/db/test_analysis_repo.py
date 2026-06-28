from src.db.database import Database
from src.db.repositories.analysis_repo import ScoreRepo, EnrichmentRepo, StoryTagRepo
from src.db.rows import ScoreRow


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    return db


def _setup_story(db):
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO story (canonical_title, first_seen_at, last_seen_at, status) "
            "VALUES (?,?,?,?)",
            ("Test Story", "2026-06-28T00:00:00Z", "2026-06-28T00:00:00Z", "new"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _setup_taxonomy(db):
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO taxonomy (dimension, code, label, sort_order) VALUES (?,?,?,?)",
            ("industry_group", "TMT", "TMT", 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


class TestScoreRepo:
    def test_add_and_latest(self, tmp_path):
        db = _db(tmp_path)
        sid = _setup_story(db)
        repo = ScoreRepo(db)

        rid = repo.add(ScoreRow(
            story_id=sid, model="deepseek-v4-flash", score=8.5,
            importance_rationale="high impact", scored_at="2026-06-28T01:00:00Z",
        ))
        assert rid > 0

        latest = repo.latest_for_story(sid)
        assert latest is not None
        assert latest.score == 8.5

        # add another score; latest should return the newest
        repo.add(ScoreRow(
            story_id=sid, model="deepseek-v4-flash", score=7.0,
            scored_at="2026-06-28T02:00:00Z",
        ))
        latest2 = repo.latest_for_story(sid)
        assert latest2.score == 7.0

    def test_latest_returns_none_for_empty(self, tmp_path):
        db = _db(tmp_path)
        repo = ScoreRepo(db)
        assert repo.latest_for_story(999) is None


class TestEnrichmentRepo:
    def test_add(self, tmp_path):
        db = _db(tmp_path)
        sid = _setup_story(db)
        repo = EnrichmentRepo(db)

        eid = repo.add(
            story_id=sid, context_text="M&A deal context",
            corroborating_sources='["source1"]', confidence="confirmed",
            created_at="2026-06-28T01:00:00Z",
        )
        assert eid > 0


class TestStoryTagRepo:
    def test_add_and_query(self, tmp_path):
        db = _db(tmp_path)
        sid = _setup_story(db)
        tid = _setup_taxonomy(db)
        repo = StoryTagRepo(db)

        repo.add(sid, tid)
        ids = repo.taxonomy_ids_for_story(sid)
        assert ids == [tid]

    def test_add_idempotent(self, tmp_path):
        db = _db(tmp_path)
        sid = _setup_story(db)
        tid = _setup_taxonomy(db)
        repo = StoryTagRepo(db)

        repo.add(sid, tid)
        repo.add(sid, tid)  # should not raise
        assert len(repo.taxonomy_ids_for_story(sid)) == 1
