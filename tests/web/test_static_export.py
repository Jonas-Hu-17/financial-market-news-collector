"""静态看板导出测试：data.json + index.html，含历史/分类/公司回顾/清洗。"""
import json
from pathlib import Path

from src.db import init_db
from src.db.migrate import ensure_web_columns
from src.db.rows import (
    BriefRow, BriefItemRow, StoryRow, RawItemRow, TaxonomyRow,
    EntityRow)
from src.db.repositories.brief_repo import BriefRepo, BriefItemRepo
from src.db.repositories.story_repo import StoryRepo, StoryMemberRepo
from src.db.repositories.raw_item_repo import RawItemRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.entity_repo import EntityRepo, StoryEntityRepo


def _seed_two_briefs(db) -> list[str]:
    """建两期 brief，不同日期，均有 tags + entities，返回日期列表。"""
    dates = []
    # taxonomy
    tr = TaxonomyRepo(db)
    t1 = tr.upsert(TaxonomyRow(dimension="industry_group", code="TMT", label="TMT"))
    t2 = tr.upsert(TaxonomyRow(dimension="product_group", code="MA", label="M&A/Advisory"))

    # entity
    er = EntityRepo(db)
    e1 = er.upsert(EntityRow(type="company", name="Acme Corp", created_at="2026-06-28T00:00:00Z"))
    e2 = er.upsert(EntityRow(type="company", name="Beta Ltd", created_at="2026-06-28T00:00:00Z"))

    for d in ("2026-06-28", "2026-06-27"):
        now = f"{d}T00:00:00Z"

        # raw_item
        ri, _ = RawItemRepo(db).upsert(RawItemRow(
            title=f"Headline {d}", summary=f"Summary {d}",
            url="https://example.com/news",
            dedup_key=f"dk:{d}", fetched_at=now, published_at=now))

        # story
        sid = StoryRepo(db).create(StoryRow(
            canonical_title=f"Headline {d}", first_seen_at=now, last_seen_at=now))
        StoryMemberRepo(db).add(sid, ri, is_primary=True)

        # tags
        StoryTagRepo(db).add(sid, t1)
        StoryTagRepo(db).add(sid, t2)

        # entities
        ser = StoryEntityRepo(db)
        ser.add(sid, e1, "primary")
        if d == "2026-06-28":
            ser.add(sid, e2, "related")

        # brief
        bid = BriefRepo(db).create(BriefRow(
            period_type="daily", period_date=d, language="zh",
            model="deepseek-v4-flash", generated_at=now, status="draft",
            market_view_text=f"综合市场观点 {d}"))

        # brief_item — one with dirty view, one clean
        bir = BriefItemRepo(db)
        view_text = f'中性影响 {d}'
        if d == "2026-06-28":
            # JSON残渣污染
            view_text = f'", "view": "中性影响 {d}"}} ' + view_text
        bir.add(BriefItemRow(
            brief_id=bid, story_id=sid, rank=1,
            headline=f"Headline {d}", summary=f"Summary {d}",
            view_text=view_text, created_at=now))
        dates.append(d)

    return dates


def test_static_export_data_json(tmp_path):
    """导出 data.json 含两期、taxonomy、entities；view 已清洗。"""
    from src.web.queries import WebQuery

    db_path = str(tmp_path / "t.db")
    db = init_db(db_path)
    _seed_two_briefs(db)

    wq = WebQuery(db)
    data = wq.export_all()

    # 结构
    assert "generated_at" in data
    assert "taxonomy" in data
    assert "entities" in data
    assert "briefs" in data

    # taxonomy
    assert len(data["taxonomy"]) >= 2
    dims = {t["dim"] for t in data["taxonomy"]}
    assert "industry_group" in dims
    assert "product_group" in dims

    # entities
    assert len(data["entities"]) == 2
    ent_names = {e["name"] for e in data["entities"]}
    assert "Acme Corp" in ent_names
    assert "Beta Ltd" in ent_names
    # Acme 跨两期，count >= 2
    acme = next(e for e in data["entities"] if e["name"] == "Acme Corp")
    assert acme["count"] >= 2

    # briefs
    assert len(data["briefs"]) == 2
    dates = {b["date"] for b in data["briefs"]}
    assert "2026-06-28" in dates
    assert "2026-06-27" in dates

    # 检查 06-28 的 item view 已清洗
    b28 = next(b for b in data["briefs"] if b["date"] == "2026-06-28")
    assert len(b28["items"]) == 1
    v = b28["items"][0]["view"]
    assert '"view"' not in v
    assert "中性影响" in v
    assert '",' not in v

    # 检查 entity 跨期回顾：Acme 在两期都出现
    for b in data["briefs"]:
        for it in b["items"]:
            eids = {e["id"] for e in it["entities"]}
            assert acme["id"] in eids


def test_static_index_html_generated(tmp_path):
    """index.html 从模板写入，含刊名/影响占位/邮箱/免责，无 data-vote。"""
    from src.web.static_export import _TEMPLATE

    html = _TEMPLATE

    assert "Financial Market News Collector" in html
    assert "1079919402@qq.com" in html
    assert "免责声明" in html
    assert "不构成任何投资建议" in html
    assert "data-vote" not in html
    # 影响渲染逻辑
    assert "影响：" in html
    # 公司回顾 panel
    assert "review-panel" in html
    assert "公司回顾" in html


def test_static_export_writes_files(tmp_path):
    """export() 写入 data.json + index.html 到指定目录。"""
    from src.web.static_export import export
    from src.db.database import Database

    # 需要真实 DB 路径，但测试里用 tmp_path 下的 db
    import src.web.static_export as se
    orig_db_path = se.Database

    db_path = str(tmp_path / "test.db")
    db = init_db(db_path)
    _seed_two_briefs(db)

    # Patch the Database constructor to use our test db
    class _FakeDB:
        pass

    def _fake_db(*a, **kw):
        return db

    se.Database = _fake_db

    try:
        out_dir = str(tmp_path / "site")
        dp, hp = export(out_dir)
        assert dp.exists()
        assert hp.exists()

        # 验证 data.json 可解析
        with open(dp, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["briefs"]) == 2

        # 验证 index.html 内容
        html = hp.read_text(encoding="utf-8")
        assert "Financial Market News Collector" in html
        assert "1079919402@qq.com" in html
    finally:
        se.Database = orig_db_path
