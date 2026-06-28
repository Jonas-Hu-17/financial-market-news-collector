from src.db.database import Database
from src.db.rows import BriefRow, BriefItemRow
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo


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


def _brief_row():
    return BriefRow(
        period_type="daily",
        period_date="2026-06-28",
        language="zh",
        model="deepseek-v4-flash",
        generated_at="2026-06-28T08:00:00Z",
        status="draft",
    )


class TestBriefRepo:
    def test_create_and_get(self, tmp_path):
        db = _db(tmp_path)
        repo = BriefRepo(db)

        bid = repo.create(_brief_row())
        assert bid > 0
        got = repo.get(bid)
        assert got is not None
        assert got.period_type == "daily"
        assert got.period_date == "2026-06-28"

    def test_set_market_view(self, tmp_path):
        db = _db(tmp_path)
        repo = BriefRepo(db)

        bid = repo.create(_brief_row())
        repo.set_market_view(bid, "市场整体平稳，M&A 活跃度上升。")
        got = repo.get(bid)
        assert got.market_view_text == "市场整体平稳，M&A 活跃度上升。"


class TestBriefItemRepo:
    def test_add_and_list(self, tmp_path):
        db = _db(tmp_path)
        brief_repo = BriefRepo(db)
        item_repo = BriefItemRepo(db)
        sid = _setup_story(db)

        bid = brief_repo.create(_brief_row())
        iid = item_repo.add(BriefItemRow(
            brief_id=bid, story_id=sid, rank=1,
            headline="Acme acquires Beta",
            view_text="该并购将整合两家公司的技术能力，对行业竞争格局产生影响。",
            created_at="2026-06-28T08:00:00Z",
        ))
        assert iid > 0

        items = item_repo.list_for_brief(bid)
        assert len(items) == 1
        assert items[0].headline == "Acme acquires Beta"
        assert items[0].view_text == "该并购将整合两家公司的技术能力，对行业竞争格局产生影响。"
