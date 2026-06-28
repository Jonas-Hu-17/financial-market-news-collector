"""全链路编排：抓取→去重→聚类→分析→brief→渲染→投递。"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
from .db.repositories.raw_item_repo import RawItemRepo
from .db.repositories.story_repo import StoryRepo, StoryMemberRepo
from .db.repositories.analysis_repo import ScoreRepo, StoryTagRepo, EnrichmentRepo
from .db.repositories.entity_repo import EntityRepo, StoryEntityRepo
from .db.repositories.taxonomy_repo import TaxonomyRepo
from .db.repositories.brief_repo import BriefRepo, BriefItemRepo
from .ingestion.service import IngestionService
from .ingestion.mapper import to_raw_item
from .embedding.service import EmbeddingService
from .embedding.vector_store import VectorStore
from .clustering.clusterer import StoryClusterer
from .analysis.financial_analyzer import FinancialAnalyzer
from .analysis.persist import AnalysisPersister
from .view.router import ViewRouter
from .view.compliance import ComplianceChecker
from .view.generator import ViewGenerator
from .view.brief_assembler import BriefAssembler
from .render.brief_renderer import BriefRenderer


class MarketNewsOrchestrator:
    def __init__(self, config: dict, db, ai_client):
        self.config = config
        self.db = db
        self.ai = ai_client
        self._scrapers = self._build_scrapers()

    def _build_scrapers(self) -> list:
        # 由 config 构建 RSS/SEC/HKEX scrapers；MVP 留待子计划2 接线
        return []

    def _window(self, force_hours: Optional[int]) -> datetime:
        hours = force_hours or self.config.get("window_hours", 24)
        return datetime.now(timezone.utc) - timedelta(hours=hours)

    async def run(self, period_type: str = "daily",
                  force_hours: Optional[int] = None) -> int:
        since = self._window(force_hours)
        # 1. 抓取
        items = []
        for sc in self._scrapers:
            try:
                items.extend(await sc.fetch(since))
            except Exception:
                continue

        # 2. 摄取 + 精确去重
        raw_repo = RawItemRepo(self.db)
        new_raw_ids = []
        for it in items:
            row = to_raw_item(it, None)
            rid, is_new = raw_repo.upsert(row)
            if is_new:
                row.id = rid
                new_raw_ids.append(row)

        # 3. 跨天聚类
        clusterer = StoryClusterer(
            EmbeddingService(), VectorStore(self.db),
            StoryRepo(self.db), StoryMemberRepo(self.db))
        analyze_story_ids = set()
        for row in new_raw_ids:
            sid, is_new_story = clusterer.assign(row)
            if is_new_story:
                analyze_story_ids.add(sid)

        # 4. 分析（仅新建 story；省 token）
        analyzer = FinancialAnalyzer(self.ai, TaxonomyRepo(self.db))
        persister = AnalysisPersister(
            ScoreRepo(self.db), StoryTagRepo(self.db),
            EntityRepo(self.db), StoryEntityRepo(self.db),
            TaxonomyRepo(self.db),
            model_name=self.config.get("model", "deepseek-chat"))
        for sid in analyze_story_ids:
            primary = self._primary_raw(sid)
            if not primary:
                continue
            res = await analyzer.analyze(primary.title, primary.summary or "")
            if res:
                persister.persist(sid, res)

        # 5. 组装 brief
        view_gen = ViewGenerator(
            self.ai,
            ViewRouter(StoryTagRepo(self.db), TaxonomyRepo(self.db)),
            ComplianceChecker())
        assembler = BriefAssembler(
            StoryRepo(self.db), ScoreRepo(self.db),
            StoryMemberRepo(self.db), raw_repo,
            BriefRepo(self.db), BriefItemRepo(self.db), view_gen)
        period_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        brief_id = await assembler.build(
            period_type, period_date,
            min_score=self.config.get("min_score", 6.0))

        # 6. 渲染 + 投递
        md = BriefRenderer(
            BriefRepo(self.db), BriefItemRepo(self.db),
            StoryRepo(self.db), StoryMemberRepo(self.db),
            raw_repo, StoryTagRepo(self.db),
            TaxonomyRepo(self.db)).render(brief_id)
        self._deliver(period_date, md)
        return brief_id

    def _primary_raw(self, story_id: int):
        ids = StoryMemberRepo(self.db).raw_items_for_story(story_id)
        return RawItemRepo(self.db).get(ids[0]) if ids else None

    def _deliver(self, period_date: str, markdown: str) -> None:
        from pathlib import Path
        out = Path(self.config.get("docs_dir", "docs")) / f"{period_date}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
