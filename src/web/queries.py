"""为 Web 渲染取结构化数据：某期 brief + 每条的 tags/url/计数。"""
from __future__ import annotations
from ..db.database import Database
from ..db.repositories.feedback_repo import FeedbackRepo


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

    def brief_for_web(self, date: str) -> dict | None:
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
            items = []
            for r in rows:
                tags = self._tags_for_story(conn, r["story_id"])
                tag_labels = [t["label"] for t in tags]
                tag_codes = [f"{t['dimension']}:{t['code']}" for t in tags]
                cnt = fb.counts(r["id"])
                items.append({
                    "id": r["id"],
                    "rank": r["rank"],
                    "headline": r["headline"] or r["canonical_title"] or "",
                    "summary": r["summary"] or "",
                    "view": r["view_text"] or "",
                    "url": r["url"] or "",
                    "tags": [{"dim": t["dimension"], "code": t["code"],
                              "label": t["label"]} for t in tags],
                    "tagcodes": ",".join(tag_codes),
                    "up": cnt["up"],
                    "down": cnt["down"],
                })
            # 收集本期所有 unique taxonomy labels 作为 filter 选项
            seen = set()
            filters = []
            for it in items:
                for t in it["tags"]:
                    key = f"{t['dim']}:{t['code']}"
                    if key not in seen:
                        seen.add(key)
                        filters.append({"code": key, "label": t["label"]})
            return {
                "date": brief["period_date"],
                "market_view": brief["market_view_text"] or "",
                "items": items,
                "filters": filters,
            }
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
