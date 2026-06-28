"""把 AnalysisResult 落库。"""
from __future__ import annotations
from datetime import datetime, timezone
from ..db.rows import ScoreRow, EntityRow

_DIMENSIONS = ["market_type", "industry_group", "product_group", "region", "asset_class"]


class AnalysisPersister:
    def __init__(self, score_repo, story_tag_repo, entity_repo,
                 story_entity_repo, taxonomy_repo, model_name: str):
        self.scores = score_repo
        self.tags = story_tag_repo
        self.entities = entity_repo
        self.story_entities = story_entity_repo
        self.tax = taxonomy_repo
        self.model_name = model_name

    def persist(self, story_id: int, result) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.scores.add(ScoreRow(
            story_id=story_id, model=self.model_name,
            score=result.score, importance_rationale=result.rationale,
            scored_at=now))
        for dim in _DIMENSIONS:
            code = result.tag_codes.get(dim)
            if not code:
                continue
            tax_id = self.tax.get_id(dim, code)
            if tax_id is not None:
                self.tags.add(story_id, tax_id)
        for e in result.entities:
            if not e.get("name"):
                continue
            eid = self.entities.upsert(EntityRow(
                type=e.get("type", "company"), name=e["name"],
                ticker=e.get("ticker"), created_at=now))
            self.story_entities.add(story_id, eid, e.get("role", "related"))
