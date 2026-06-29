"""跨天 story 聚类：相似归入已有 story（标记 updated），否则新建。"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from ..db.rows import RawItemRow, StoryRow


class StoryClusterer:
    def __init__(self, embedding, vector_store, story_repo, member_repo,
                 *, similarity_threshold: float = 0.82, lookback_days: int = 7):
        self.embedding = embedding
        self.vs = vector_store
        self.stories = story_repo
        self.members = member_repo
        self.threshold = similarity_threshold
        self.lookback_days = lookback_days

    def assign(self, raw_item: RawItemRow, vec: list[float] | None = None) -> tuple[int, bool]:
        if vec is None:
            text = f"{raw_item.title}\n{raw_item.summary or ''}"
            vec = self.embedding.embed_one(text)
        self.vs.add(raw_item.id, vec)

        since = (datetime.now(timezone.utc) - timedelta(days=self.lookback_days)).isoformat()
        recent_ids = {rid for rid in self._recent_member_item_ids(since)
                      if rid != raw_item.id}
        now = datetime.now(timezone.utc).isoformat()

        if recent_ids:
            neighbors = self.vs.knn(vec, k=3, allowed_ids=recent_ids)
            for nid, dist in neighbors:
                cos = 1.0 - (dist * dist) / 2.0   # 归一化向量 L2→cos
                if cos >= self.threshold:
                    story_id = self._story_of_item(nid)
                    if story_id is not None:
                        self.members.add(story_id, raw_item.id, is_primary=False)
                        self.stories.update_status(story_id, "updated", now)
                        return story_id, False

        new_id = self.stories.create(StoryRow(
            canonical_title=raw_item.title, first_seen_at=now,
            last_seen_at=now, last_update_at=now, status="new"))
        self.members.add(new_id, raw_item.id, is_primary=True)
        return new_id, True

    def _recent_member_item_ids(self, since_iso: str) -> list[int]:
        """反向直查：JOIN story+story_member 一次 SQL 取最近 N 天成员 raw_item_id 集合。"""
        conn = self.members.db.connect()
        try:
            rows = conn.execute(
                "SELECT sm.raw_item_id FROM story_member sm "
                "JOIN story s ON s.id = sm.story_id "
                "WHERE s.last_seen_at >= ?",
                (since_iso,),
            ).fetchall()
            return [r["raw_item_id"] for r in rows]
        finally:
            conn.close()

    def _story_of_item(self, raw_item_id: int):
        return self.members.story_id_for_raw_item(raw_item_id)
