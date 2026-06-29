"""全链路编排：抓取→去重→聚类→分析→brief→渲染→投递。"""
from __future__ import annotations
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional
from .models import RSSSourceConfig
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
        self._http = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        self._scrapers = self._build_scrapers()

    def _build_scrapers(self) -> list:
        scrapers = []
        sources = self.config.get("sources", {})

        # RSS feeds
        rss_cfgs = sources.get("rss", [])
        if rss_cfgs:
            from .scrapers.rss import RSSScraper
            rss_sources = []
            for r in rss_cfgs:
                if isinstance(r, dict):
                    rss_sources.append(RSSSourceConfig(
                        name=r.get("name", ""),
                        url=r.get("url", ""),
                        enabled=r.get("enabled", True),
                        category=r.get("category"),
                    ))
                elif isinstance(r, RSSSourceConfig):
                    rss_sources.append(r)
            if rss_sources:
                scrapers.append(RSSScraper(rss_sources, self._http))

        # SEC EDGAR
        sec_cfg = sources.get("sec_edgar")
        if sec_cfg and sec_cfg.get("enabled"):
            from .scrapers.sec_edgar import SECEdgarScraper
            scrapers.append(SECEdgarScraper(sec_cfg, self._http))

        # HKEX
        hkex_cfg = sources.get("hkex")
        if hkex_cfg and hkex_cfg.get("enabled"):
            from .scrapers.hkex import HKEXScraper
            scrapers.append(HKEXScraper(hkex_cfg, self._http))

        return scrapers

    def _window(self, force_hours: Optional[int]) -> datetime:
        hours = force_hours or self.config.get("window_hours", 24)
        return datetime.now(timezone.utc) - timedelta(hours=hours)

    async def run(self, period_type: str = "daily",
                  force_hours: Optional[int] = None) -> int:
        since = self._window(force_hours)
        # 1. 并发抓取（各 scraper 独立，并发度由 asyncio.gather 自然驱动）
        async def _fetch_one(sc):
            try:
                return await sc.fetch(since)
            except Exception:
                return []
        fetched_lists = await asyncio.gather(*[_fetch_one(sc) for sc in self._scrapers])
        items = []
        for fl in fetched_lists:
            items.extend(fl)
        # 关闭 http 客户端
        try:
            await self._http.aclose()
        except Exception:
            pass

        # 2. 摄取 + 精确去重
        raw_repo = RawItemRepo(self.db)
        new_raw_ids = []
        for it in items:
            row = to_raw_item(it, None)
            rid, is_new = raw_repo.upsert(row)
            if is_new:
                row.id = rid
                new_raw_ids.append(row)

        # 3. 跨天聚类（批量 embedding，一次模型调用编码全部新条目）
        emb_svc = EmbeddingService()
        texts = [f"{r.title}\n{r.summary or ''}" for r in new_raw_ids]
        vecs = emb_svc.embed(texts) if texts else []
        clusterer = StoryClusterer(
            emb_svc, VectorStore(self.db),
            StoryRepo(self.db), StoryMemberRepo(self.db))
        analyze_story_ids = set()
        for row, vec in zip(new_raw_ids, vecs):
            sid, is_new_story = clusterer.assign(row, vec=vec)
            if is_new_story:
                analyze_story_ids.add(sid)

        # 4. 分析（仅新建 story；省 token）
        analyzer = FinancialAnalyzer(self.ai, TaxonomyRepo(self.db))
        persister = AnalysisPersister(
            ScoreRepo(self.db), StoryTagRepo(self.db),
            EntityRepo(self.db), StoryEntityRepo(self.db),
            TaxonomyRepo(self.db),
            model_name=self.config.get("model", "deepseek-v4-flash"))

        concurrency = self.config.get("llm_concurrency", 6)
        batch_size = self.config.get("llm_batch_size", 15)

        # 按 (title, summary) 收集待分析 story
        pending: list[tuple[int, str, str]] = []   # [(sid, title, summary)]
        for sid in sorted(analyze_story_ids):
            primary = self._primary_raw(sid)
            if primary:
                pending.append((sid, primary.title, primary.summary or ""))

        if not pending:
            pending = []   # no-op below

        sem = asyncio.Semaphore(concurrency)

        async def _analyze_batch_block(block: list[tuple[int, str, str]]):
            items = [(str(sid), title, summary) for sid, title, summary in block]
            keyed = [(sid, title, summary) for sid, title, summary in block]
            async with sem:
                batch_result = await analyzer.analyze_batch(
                    [(title, summary) for _, title, summary in keyed])
            for sid, title, summary in keyed:
                res = batch_result.get(str(sid))
                if res is None:
                    # 兜底：单条 analyze
                    try:
                        res = await analyzer.analyze(title, summary)
                    except Exception:
                        res = None
                if res:
                    persister.persist(sid, res)

        # 分块并发
        chunks = [pending[i:i + batch_size]
                  for i in range(0, len(pending), batch_size)]
        await asyncio.gather(*[_analyze_batch_block(ch) for ch in chunks])

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
            min_score=self.config.get("min_score", 6.0),
            max_items=self.config.get("max_items", 12),
            llm_concurrency=concurrency)

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
