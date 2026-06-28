from src.db.database import Database
from src.db.rows import StoryRow
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.init_schema()
    return db


def _story_row(title="Acme M&A deal", status="new"):
    return StoryRow(
        canonical_title=title,
        first_seen_at="2026-06-28T00:00:00Z",
        last_seen_at="2026-06-28T00:00:00Z",
        status=status,
    )


class TestStoryRepo:
    def test_create_and_get(self, tmp_path):
        db = _db(tmp_path)
        repo = StoryRepo(db)
        sid = repo.create(_story_row())
        assert sid > 0
        got = repo.get(sid)
        assert got is not None
        assert got.canonical_title == "Acme M&A deal"

    def test_update_status(self, tmp_path):
        db = _db(tmp_path)
        repo = StoryRepo(db)
        sid = repo.create(_story_row(status="new"))
        repo.update_status(sid, "ongoing", "2026-06-29T00:00:00Z")
        got = repo.get(sid)
        assert got.status == "ongoing"
        assert got.last_update_at == "2026-06-29T00:00:00Z"

    def test_recent(self, tmp_path):
        db = _db(tmp_path)
        repo = StoryRepo(db)
        repo.create(_story_row("old story"))
        # story 2: seen more recently
        s2 = _story_row("recent story")
        s2.last_seen_at = "2026-07-01T00:00:00Z"
        repo.create(s2)
        # should return both since since_iso is before both
        recent = repo.recent("2026-06-01T00:00:00Z")
        assert len(recent) == 2
        # should only return the recent one
        recent2 = repo.recent("2026-06-30T00:00:00Z")
        assert len(recent2) == 1
        assert recent2[0].canonical_title == "recent story"


class TestStoryMemberRepo:
    def test_add_and_query(self, tmp_path):
        db = _db(tmp_path)
        story_repo = StoryRepo(db)
        member_repo = StoryMemberRepo(db)

        sid = story_repo.create(_story_row())
        # need a raw_item to reference; insert manually
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO raw_item (title, fetched_at, dedup_key) VALUES (?,?,?)",
                ("item1", "2026-06-28T00:00:00Z", "dk1"),
            )
            conn.execute(
                "INSERT INTO raw_item (title, fetched_at, dedup_key) VALUES (?,?,?)",
                ("item2", "2026-06-28T00:00:00Z", "dk2"),
            )
            conn.commit()
        finally:
            conn.close()

        member_repo.add(sid, 1, is_primary=True)
        member_repo.add(sid, 2, is_primary=False)

        item_ids = member_repo.raw_items_for_story(sid)
        assert sorted(item_ids) == [1, 2]

    def test_add_idempotent(self, tmp_path):
        db = _db(tmp_path)
        story_repo = StoryRepo(db)
        member_repo = StoryMemberRepo(db)

        sid = story_repo.create(_story_row())
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO raw_item (title, fetched_at, dedup_key) VALUES (?,?,?)",
                ("item", "2026-06-28T00:00:00Z", "dk"),
            )
            conn.commit()
        finally:
            conn.close()

        member_repo.add(sid, 1)
        # adding again should not raise (PK constraint)
        member_repo.add(sid, 1)
        assert len(member_repo.raw_items_for_story(sid)) == 1
