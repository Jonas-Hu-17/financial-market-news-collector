"""为 Web 渲染取结构化数据：某期 brief + 每条的 tags/url/计数。"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from ..db.database import Database
from ..db.repositories.feedback_repo import FeedbackRepo


def _clean_view(text: str) -> str:
    """渲染时剥掉模型偶尔泄漏的 JSON 残渣，覆盖 view/summary 字段名前缀。
    仅在检测到 JSON 残渣时清洗，正常 view 原样返回。"""
    if not text:
        return ""
    s = text.strip()
    # 检测 JSON 残渣特征
    has_json = (
        '"view"' in s or '"summary"' in s
        or 'summary":' in s or 'view":' in s
        or s.startswith('",') or s.startswith('"}') or s.startswith('{')
    )
    if not has_json:
        return s

    # 1) 优先提取 "view" 字段值
    m = re.search(r'"view"\s*:\s*"(.+?)"\s*[},]?\s*$', s, re.S)
    if not m:
        m = re.search(r'"view"\s*:\s*"([^"]+)"', s)
    if m:
        return m.group(1).strip()

    # 2) 提取 "summary" 字段值（当 view 字段不存在时）
    if '"summary"' in s or 'summary":' in s:
        m = re.search(r'"summary"\s*:\s*"(.+?)"\s*[},]?\s*$', s, re.S)
        if not m:
            m = re.search(r'"summary"\s*:\s*"([^"]+)"', s)
        if m:
            return m.group(1).strip()

    # 3) 去掉 summary": 或 view": 前缀（无引号包裹的正文）
    s = re.sub(r'^"?summary"?\s*:\s*"?(.+?)"?\s*$', r'\1', s)
    s = re.sub(r'^"?view"?\s*:\s*"?(.+?)"?\s*$', r'\1', s)

    # 4) 兜底：迭代 strip 开头的 JSON 符号和结尾的 JSON 符号，直到稳定
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'^[\s",}{]+', '', s)
        s = re.sub(r'[]\s"}\\]+$', '', s)
    return s.strip()


@dataclass
class BriefWebItem:
    id: int
    rank: int
    headline: str
    summary: str
    view: str
    url: str
    tags: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    tagcodes: str = ""
    up: int = 0
    down: int = 0


@dataclass
class BriefWebData:
    date: str = ""
    market_view: str = ""
    items: list[BriefWebItem] = field(default_factory=list)
    filters: list[dict] = field(default_factory=list)


class WebQuery:
    def __init__(self, db: Database):
        self.db = db

    def latest_date(self) -> str | None:
        conn = self.db.connect()
        try:
            r = conn.execute(
                "SELECT period_date FROM brief ORDER BY period_date DESC LIMIT 1"
            ).fetchone()
            return r["period_date"] if r else None
        finally:
            conn.close()

    def list_dates(self, limit: int = 30) -> list[str]:
        conn = self.db.connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT period_date FROM brief ORDER BY period_date DESC "
                "LIMIT ?", (limit,)
            ).fetchall()
            return [r["period_date"] for r in rows]
        finally:
            conn.close()

    def brief_for_web(self, date: str) -> BriefWebData | None:
        conn = self.db.connect()
        try:
            brief = conn.execute(
                "SELECT * FROM brief WHERE period_date=? ORDER BY generated_at DESC "
                "LIMIT 1", (date,)
            ).fetchone()
            if not brief:
                return None
            rows = conn.execute(
                "SELECT bi.*, ri.url, s.canonical_title "
                "FROM brief_item bi "
                "JOIN story s ON bi.story_id = s.id "
                "LEFT JOIN story_member sm ON s.id = sm.story_id AND sm.is_primary=1 "
                "LEFT JOIN raw_item ri ON sm.raw_item_id = ri.id "
                "WHERE bi.brief_id=? "
                "ORDER BY bi.rank",
                (brief["id"],)
            ).fetchall()
            fb = FeedbackRepo(self.db)
            data = BriefWebData(
                date=brief["period_date"],
                market_view=brief["market_view_text"] or "",
            )
            seen = set()
            for r in rows:
                tags = self._tags_for_story(conn, r["story_id"])
                tag_codes = [f"{t['dimension']}:{t['code']}" for t in tags]
                cnt = fb.counts(r["id"])
                item = BriefWebItem(
                    id=r["id"],
                    rank=r["rank"],
                    headline=r["headline"] or r["canonical_title"] or "",
                    summary=r["summary"] or "",
                    view=_clean_view(r["view_text"] or ""),
                    url=r["url"] or "",
                    tags=[{"dim": t["dimension"], "code": t["code"],
                           "label": t["label"]} for t in tags],
                    tagcodes=",".join(tag_codes),
                    up=cnt["up"],
                    down=cnt["down"],
                )
                data.items.append(item)
                for t in tags:
                    key = f"{t['dimension']}:{t['code']}"
                    if key not in seen:
                        seen.add(key)
                        data.filters.append({"code": key, "label": t["label"]})
            return data
        finally:
            conn.close()

    def _tags_for_story(self, conn, story_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT t.dimension, t.code, t.label "
            "FROM story_tag st JOIN taxonomy t ON st.taxonomy_id = t.id "
            "WHERE st.story_id = ?", (story_id,)
        ).fetchall()
        return [{"dimension": r["dimension"], "code": r["code"],
                 "label": r["label"]} for r in rows]

    def _entities_for_story(self, conn, story_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT e.id, e.name FROM entity e "
            "JOIN story_entity se ON e.id = se.entity_id "
            "WHERE se.story_id = ?", (story_id,)
        ).fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]

    def export_all(self) -> dict:
        """导出全部历史 brief 数据为 data.json 结构。"""
        from datetime import datetime, timezone
        conn = self.db.connect()
        try:
            # taxonomy 选项
            tax_rows = conn.execute(
                "SELECT dimension, code, label FROM taxonomy ORDER BY dimension, sort_order"
            ).fetchall()
            taxonomy = [
                {"dim": r["dimension"], "code": r["code"], "label": r["label"]}
                for r in tax_rows
            ]

            # 实体清单（含被提及次数，按次数降序）
            entity_rows = conn.execute(
                """SELECT e.id, e.name, COUNT(se.story_id) AS cnt
                   FROM entity e
                   JOIN story_entity se ON e.id = se.entity_id
                   GROUP BY e.id, e.name
                   ORDER BY cnt DESC""").fetchall()
            entities = [
                {"id": r["id"], "name": r["name"], "count": r["cnt"]}
                for r in entity_rows
            ]

            # 全部 brief
            brief_rows = conn.execute(
                "SELECT * FROM brief ORDER BY period_date DESC"
            ).fetchall()

            briefs = []
            for brief in brief_rows:
                items = []
                item_rows = conn.execute(
                    """SELECT bi.*, ri.url, s.canonical_title
                       FROM brief_item bi
                       JOIN story s ON bi.story_id = s.id
                       LEFT JOIN story_member sm ON s.id = sm.story_id AND sm.is_primary=1
                       LEFT JOIN raw_item ri ON sm.raw_item_id = ri.id
                       WHERE bi.brief_id=?
                       ORDER BY bi.rank""",
                    (brief["id"],)
                ).fetchall()
                for r in item_rows:
                    tags = self._tags_for_story(conn, r["story_id"])
                    ents = self._entities_for_story(conn, r["story_id"])
                    items.append({
                        "rank": r["rank"],
                        "headline": r["headline"] or r["canonical_title"] or "",
                        "summary": r["summary"] or "",
                        "view": _clean_view(r["view_text"] or ""),
                        "url": r["url"] or "",
                        "tags": [{"dim": t["dimension"], "code": t["code"],
                                  "label": t["label"]} for t in tags],
                        "entities": ents,
                    })
                briefs.append({
                    "date": brief["period_date"],
                    "market_view": brief["market_view_text"] or "",
                    "items": items,
                })
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "taxonomy": taxonomy,
                "entities": entities,
                "briefs": briefs,
            }
        finally:
            conn.close()
