from src.db.database import Database
from src.db.repositories.entity_repo import EntityRepo, StoryEntityRepo, WatchlistRepo
from src.db.rows import EntityRow


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


def _entity(name="Acme Corp", type="company"):
    return EntityRow(type=type, name=name, created_at="2026-06-28T00:00:00Z")


class TestEntityRepo:
    def test_upsert_inserts_new(self, tmp_path):
        db = _db(tmp_path)
        repo = EntityRepo(db)
        eid = repo.upsert(_entity("Acme Corp"))
        assert eid > 0

    def test_upsert_is_idempotent(self, tmp_path):
        db = _db(tmp_path)
        repo = EntityRepo(db)
        eid1 = repo.upsert(_entity("Acme Corp"))
        eid2 = repo.upsert(_entity("Acme Corp"))
        assert eid1 == eid2

    def test_get(self, tmp_path):
        db = _db(tmp_path)
        repo = EntityRepo(db)
        eid = repo.upsert(_entity("Beta Ltd"))
        got = repo.get(eid)
        assert got is not None
        assert got.name == "Beta Ltd"


class TestStoryEntityRepo:
    def test_add_and_stories_for_entity(self, tmp_path):
        db = _db(tmp_path)
        sid1 = _setup_story(db)
        entity_repo = EntityRepo(db)
        story_entity_repo = StoryEntityRepo(db)

        eid = entity_repo.upsert(_entity("Acme"))
        story_entity_repo.add(sid1, eid, "primary")
        story_ids = story_entity_repo.stories_for_entity(eid)
        assert sid1 in story_ids

        # Add another story for same entity
        conn = db.connect()
        try:
            cur = conn.execute(
                "INSERT INTO story (canonical_title, first_seen_at, last_seen_at, status) "
                "VALUES (?,?,?,?)",
                ("Story 2", "2026-06-29T00:00:00Z", "2026-06-29T00:00:00Z", "new"),
            )
            conn.commit()
            sid2 = cur.lastrowid
        finally:
            conn.close()
        story_entity_repo.add(sid2, eid, "related")
        assert len(story_entity_repo.stories_for_entity(eid)) == 2


class TestWatchlistRepo:
    def test_add_and_list(self, tmp_path):
        db = _db(tmp_path)
        entity_repo = EntityRepo(db)
        watchlist_repo = WatchlistRepo(db)

        eid = entity_repo.upsert(_entity("Acme"))
        wid = watchlist_repo.add(entity_id=eid, note="Interesting", added_at="2026-06-28T00:00:00Z")
        assert wid > 0

        entity_ids = watchlist_repo.list()
        assert eid in entity_ids
