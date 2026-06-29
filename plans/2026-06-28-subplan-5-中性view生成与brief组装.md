# 子计划 5：中性 view 生成（skill 路由）+ brief 组装

> **致执行者：** 逐任务 TDD。前置：子计划 1–4 完成。这是系统价值核心，提示词模板已由 Opus 从 Anthropic 金融 skill 提炼，**请勿弱化中性/无建议约束**。

**目标：** 按 story 的分类标签路由到对应 view 提示词模板（从 morning-note/earnings-analysis/sector-overview/thematic 提炼，但**剥离一切方向性结论**），用 DeepSeek 生成每条 story 的**中性影响陈述**与整期**综合市场观点**；输出层做建议性措辞检查；把高分 story 组装成 brief 落库。

**架构：**
- `view_templates.py`：一个**通用中性 system prompt**（合规底线）+ 若干**按类型的 user 模板**（每个内嵌对应 skill 提炼的分析维度）。
- `ViewRouter`：根据 story 的 `product_group`/`industry_group`/`market_type` 标签选模板。
- `ViewGenerator`：调 DeepSeek 生成 `view_text`（单条）与 `market_view_text`（整期）。
- `ComplianceChecker`：正则/关键词扫描违规建议性措辞，命中则要求重写或剥离。
- `BriefAssembler`：取当期高分 story → 生成 view → 排序 → 写 `brief`/`brief_item` + 免责声明。

**技术栈：** Horizon `ai/client.py`、子计划1/4 的 Repos。

## Global Constraints
🔒 **绝对中性、无投资建议**：禁止 buy/sell/long/short/overweight/underweight/目标价/建议买入卖出/看多看空。view 只陈述「这条信息对市场机制、相关方、估值要素可能产生什么影响」，并标注不确定性。每期带免责声明。

## 文件结构
- 创建 `src/view/__init__.py`
- 创建 `src/view/view_templates.py` — system + 各类型 user 模板
- 创建 `src/view/router.py` — `ViewRouter`
- 创建 `src/view/generator.py` — `ViewGenerator`
- 创建 `src/view/compliance.py` — `ComplianceChecker`
- 创建 `src/view/brief_assembler.py` — `BriefAssembler`
- 测试 `tests/view/`

---

## Task 1: 中性 view 提示词模板库（提炼自 skill）

**Files:**
- Create: `src/view/view_templates.py`
- Test: `tests/view/test_view_templates.py`

**Interfaces:**
- Produces:
  - `NEUTRAL_SYSTEM: str`（合规底线 system prompt）
  - `TEMPLATES: dict[str, str]`（键：`ma`/`earnings`/`sector_macro`/`thematic`/`primary_market`/`default`；值：user 模板，含 `{title}`、`{summary}`、`{context}` 占位）
  - `MARKET_VIEW_SYSTEM: str` 与 `build_market_view_user(items: list[str]) -> str`

- [ ] **Step 1: 写测试 `tests/view/test_view_templates.py`**

```python
from src.view.view_templates import NEUTRAL_SYSTEM, TEMPLATES, MARKET_VIEW_SYSTEM

def test_system_enforces_neutrality():
    s = NEUTRAL_SYSTEM.lower()
    assert "not" in s and "advice" in s
    assert "neutral" in s

def test_templates_cover_routes():
    for k in ["ma","earnings","sector_macro","thematic","primary_market","default"]:
        assert k in TEMPLATES
        assert "{title}" in TEMPLATES[k]

def test_ma_template_has_skill_dimensions():
    # 提炼自 competitive-analysis/comps：战略契合、对价/倍数、相关方
    t = TEMPLATES["ma"]
    assert "strategic" in t.lower() or "战略" in t
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/view/view_templates.py`**

```python
"""中性 view 提示词模板。各 user 模板内嵌对应 Anthropic 金融 skill 的分析维度，
但严格剥离方向性结论。system 为合规底线。"""
from __future__ import annotations

NEUTRAL_SYSTEM = """You are a financial markets information analyst writing a neutral \
impact note for a single news item. Your job is to explain WHAT the development is and \
HOW it could affect market mechanics, the parties involved, and valuation drivers — \
strictly factually and neutrally.

HARD RULES (compliance — never violate):
- This is NOT investment advice. Do NOT recommend buying, selling, holding, \
overweighting, or underweighting anything.
- Do NOT give price targets, ratings, or directional calls (no bullish/bearish stance).
- State impacts as possibilities with their drivers and uncertainties, not predictions.
- Be concise (2-4 sentences). Write in the user's language (Chinese unless item is clearly English-only context).
- If facts are unverified, say so."""

# 每个模板提炼自对应 skill 的分析骨架（去掉方向性输出）
_MA = """A merger / acquisition / deal item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral impact note covering (framework distilled from competitive-analysis & comps):
- Strategic rationale / fit implied by the deal (what capability or market it adds)
- Parties and their roles; deal consideration or implied multiple if stated
- Which valuation drivers (synergies, market structure, competitive dynamics) it touches
Do NOT judge whether it is good/bad for any stock."""

_EARNINGS = """An earnings / results item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral impact note (framework distilled from earnings-analysis Parse→Compare→Diagnose):
- What was reported vs. prior period/expectations (beat/miss/in-line if stated)
- Which operational drivers changed (revenue mix, margins, guidance)
- What it signals about the forward operating trajectory
Stop at diagnosis — do NOT give a buy/sell verdict or price target."""

_SECTOR = """A sector / macro / policy item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral impact note (framework distilled from sector-overview):
- The sector/macro development and its driver
- Which parts of the value chain or which market segments it touches
- Possible second-order effects on demand, costs, or valuation multiples (as possibilities)
Do NOT recommend positioning."""

_THEMATIC = """A thematic / secular-trend item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral impact note (framework distilled from thematic-investment-research DRIVER lens):
- The structural driver and whether it appears durable vs. temporary
- Who the beneficiaries / exposed parties are along the value chain
- Which leading indicators would confirm or refute the trend
Do NOT make a directional investment call."""

_PRIMARY = """A primary-market (PE/VC) financing item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral impact note:
- Round/stage, amount, and parties (investors / company) if stated
- What it implies about the sector's funding environment and the company's stage
- Read-across to comparable private/public names (as factual context only)
Do NOT give an investment recommendation."""

_DEFAULT = """A financial markets news item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

Write a neutral 2-4 sentence impact note: what it is, which parties/markets it touches, \
and which valuation or market-mechanic drivers could be affected (as possibilities). \
No advice, no direction, no price target."""

TEMPLATES = {
    "ma": _MA, "earnings": _EARNINGS, "sector_macro": _SECTOR,
    "thematic": _THEMATIC, "primary_market": _PRIMARY, "default": _DEFAULT,
}

MARKET_VIEW_SYSTEM = """You are writing a neutral end-of-brief market overview. \
Synthesize the day's items into a short factual picture of the cross-cutting themes \
and where activity concentrated. NOT investment advice: no recommendations, no \
directional calls, no price targets. 4-7 sentences, in the user's language."""


def build_market_view_user(items: list[str]) -> str:
    joined = "\n".join(f"- {x}" for x in items)
    return f"""Today's item impact notes:
{joined}

Write a neutral synthesis: the dominant themes, where deal/market activity clustered \
(by sector/region/product), and notable cross-currents. Stay descriptive; no advice."""
```

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: 提交** — `git commit -m "feat(view): neutral view prompt templates distilled from finance skills"`

---

## Task 2: ViewRouter（按标签选模板）

**Files:**
- Create: `src/view/router.py`
- Test: `tests/view/test_router.py`

**Interfaces:**
- Consumes: `TaxonomyRepo`、`StoryTagRepo`、`TEMPLATES`
- Produces:
  - `ViewRouter(story_tag_repo, taxonomy_repo)`
  - `route(story_id: int) -> str`（返回模板 key）。规则（优先级从上到下）：
    - product_group ∈ {MA} → `ma`
    - product_group ∈ {VC, PEBuyout, FundClosing, PreIPO, PrivatePlacement} 或 market_type=primary → `primary_market`
    - 有 earnings 信号（industry 任意 + 标题/标签暗示财报；MVP 简化：tag 无专门 earnings 轴时归 default 由内容触发）→ 由调用方传入 hint，MVP 先按 product_group 无匹配且 region/sector 主导 → `sector_macro`
    - 命中 thematic（无具体公司实体且 region=Global）→ `thematic`
    - 否则 → `default`

- [ ] **Step 1: 写测试 `tests/view/test_router.py`**

```python
from datetime import datetime, timezone
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.db.rows import StoryRow
from src.view.router import ViewRouter

def _story_with_tags(db, codes):
    now = datetime.now(timezone.utc).isoformat()
    sid = StoryRepo(db).create(StoryRow(canonical_title="x", first_seen_at=now, last_seen_at=now))
    tax, st = TaxonomyRepo(db), StoryTagRepo(db)
    for dim, code in codes.items():
        st.add(sid, tax.get_id(dim, code))
    return sid

def test_routes_ma(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    sid = _story_with_tags(db, {"product_group":"MA"})
    assert ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)).route(sid) == "ma"

def test_routes_primary_market(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    sid = _story_with_tags(db, {"product_group":"VC","market_type":"primary"})
    assert ViewRouter(StoryTagRepo(db), TaxonomyRepo(db)).route(sid) == "primary_market"
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/view/router.py`**

```python
"""按 story 分类标签路由到 view 模板。"""
from __future__ import annotations

_PRIMARY_PRODUCTS = {"VC", "PEBuyout", "FundClosing", "PreIPO", "PrivatePlacement"}


class ViewRouter:
    def __init__(self, story_tag_repo, taxonomy_repo):
        self.tags = story_tag_repo
        self.tax = taxonomy_repo

    def _codes(self, story_id: int) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for tax_id in self.tags.taxonomy_ids_for_story(story_id):
            row = self._tax_by_id(tax_id)
            if row:
                out.setdefault(row.dimension, set()).add(row.code)
        return out

    def _tax_by_id(self, tax_id: int):
        for dim in ["market_type","industry_group","product_group","region","asset_class"]:
            for r in self.tax.list_by_dimension(dim):
                if r.id == tax_id:
                    return r
        return None

    def route(self, story_id: int) -> str:
        c = self._codes(story_id)
        product = c.get("product_group", set())
        market = c.get("market_type", set())
        region = c.get("region", set())
        if "MA" in product:
            return "ma"
        if product & _PRIMARY_PRODUCTS or "primary" in market:
            return "primary_market"
        if {"ECM","DCM","LevFin","Restructuring"} & product:
            return "sector_macro"
        if "Global" in region and not product:
            return "thematic"
        if region or c.get("industry_group"):
            return "sector_macro"
        return "default"
```

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: 提交** — `git commit -m "feat(view): tag-based view template router"`

---

## Task 3: ComplianceChecker（建议性措辞拦截）

**Files:**
- Create: `src/view/compliance.py`
- Test: `tests/view/test_compliance.py`

**Interfaces:**
- Produces:
  - `@dataclass Violation(term:str, span:str)`
  - `ComplianceChecker(extra_terms: list[str]|None=None)`
  - `scan(text: str) -> list[Violation]`（命中投资建议性措辞返回违规项；中英文）
  - `is_clean(text: str) -> bool`

- [ ] **Step 1: 写测试 `tests/view/test_compliance.py`**

```python
from src.view.compliance import ComplianceChecker

def test_flags_directional_terms():
    c = ComplianceChecker()
    assert not c.is_clean("We recommend buying this stock, price target $50")
    assert not c.is_clean("建议买入，目标价 50 元")
    assert c.scan("看多该板块")

def test_neutral_passes():
    c = ComplianceChecker()
    assert c.is_clean("该交易可能影响行业竞争格局与相关方的估值要素。")
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/view/compliance.py`**

```python
"""中性合规检查：拦截投资建议性措辞。"""
from __future__ import annotations
import re
from dataclasses import dataclass

_TERMS = [
    r"\bbuy\b", r"\bsell\b", r"\blong\b", r"\bshort\b", r"overweight",
    r"underweight", r"price target", r"\brating\b", r"bullish", r"bearish",
    r"recommend", r"建议买入", r"建议卖出", r"买入", r"卖出", r"增持", r"减持",
    r"看多", r"看空", r"目标价", r"强烈推荐",
]


@dataclass
class Violation:
    term: str
    span: str


class ComplianceChecker:
    def __init__(self, extra_terms: list[str] | None = None):
        terms = _TERMS + (extra_terms or [])
        self._patterns = [re.compile(t, re.IGNORECASE) for t in terms]

    def scan(self, text: str) -> list[Violation]:
        found = []
        for p in self._patterns:
            m = p.search(text)
            if m:
                found.append(Violation(term=p.pattern, span=m.group(0)))
        return found

    def is_clean(self, text: str) -> bool:
        return not self.scan(text)
```

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: 提交** — `git commit -m "feat(view): compliance checker for advisory language"`

---

## Task 4: ViewGenerator + BriefAssembler

**Files:**
- Create: `src/view/generator.py`
- Create: `src/view/brief_assembler.py`
- Test: `tests/view/test_generator.py`、`tests/view/test_brief_assembler.py`

**Interfaces:**
- `ViewGenerator(ai_client, router, compliance)`
  - `async generate_item_view(story_id:int, title:str, summary:str, context:str="") -> str`（路由选模板→调模型→合规扫描，命中则追加一次「请去除任何建议性措辞，仅保留中性影响陈述」重写；仍不洁则返回剥离违规句后的安全降级文本）
  - `async generate_market_view(item_views: list[str]) -> str`
- `BriefAssembler(story_repo, score_repo, member_repo, raw_item_repo, brief_repo, brief_item_repo, view_generator)`
  - `async build(period_type:str, period_date:str, *, min_score:float=6.0, max_items:int=20, language:str="zh") -> int`（取当期分数≥min_score 的 story 按分降序取前 max_items；对每条用主 raw_item 的标题+摘要生成 view；写 brief + brief_item(含 rank/headline/summary/view_text)；汇总生成 market_view_text；返回 brief_id）

- [ ] **Step 1: 写测试（假 AI）`tests/view/test_generator.py`**

```python
import asyncio
from src.db import init_db
from src.db.repositories.story_repo import StoryRepo
from src.db.repositories.analysis_repo import StoryTagRepo
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.view.router import ViewRouter
from src.view.compliance import ComplianceChecker
from src.view.generator import ViewGenerator

class FakeAI:
    def __init__(self, seq): self.seq=list(seq); self.calls=[]
    async def complete(self, system, user):
        self.calls.append((system,user)); return self.seq.pop(0)

def test_generate_item_view_clean(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc).isoformat()
    sid=StoryRepo(db).create(__import__("src.db.rows",fromlist=["StoryRow"]).StoryRow(
        canonical_title="x", first_seen_at=now, last_seen_at=now))
    gen=ViewGenerator(FakeAI(["该交易可能影响行业竞争格局。"]),
        ViewRouter(StoryTagRepo(db),TaxonomyRepo(db)), ComplianceChecker())
    out=asyncio.run(gen.generate_item_view(sid,"Acme buys Beta","deal"))
    assert "竞争格局" in out

def test_generate_item_view_rewrites_on_violation(tmp_path):
    db = init_db(str(tmp_path/"t.db"))
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc).isoformat()
    sid=StoryRepo(db).create(__import__("src.db.rows",fromlist=["StoryRow"]).StoryRow(
        canonical_title="x", first_seen_at=now, last_seen_at=now))
    # 第一次返回含违规措辞，第二次返回干净
    gen=ViewGenerator(FakeAI(["建议买入该股票。","该消息可能影响相关方估值要素。"]),
        ViewRouter(StoryTagRepo(db),TaxonomyRepo(db)), ComplianceChecker())
    out=asyncio.run(gen.generate_item_view(sid,"x","y"))
    assert "建议买入" not in out
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `src/view/generator.py`**

```python
"""中性 view 生成：路由选模板 → 调模型 → 合规扫描/重写。"""
from __future__ import annotations
import re
from .view_templates import (NEUTRAL_SYSTEM, TEMPLATES, MARKET_VIEW_SYSTEM,
                             build_market_view_user)

_REWRITE_HINT = ("\n\nIMPORTANT: Your previous answer contained advisory or directional "
                 "language. Rewrite it as a strictly neutral impact statement: no "
                 "buy/sell/hold, no rating, no price target, no bullish/bearish stance.")


class ViewGenerator:
    def __init__(self, ai_client, router, compliance):
        self.ai = ai_client
        self.router = router
        self.compliance = compliance

    async def generate_item_view(self, story_id: int, title: str,
                                 summary: str, context: str = "") -> str:
        key = self.router.route(story_id)
        user = TEMPLATES[key].format(title=title, summary=summary or "(none)",
                                     context=context or "(none)")
        text = await self.ai.complete(NEUTRAL_SYSTEM, user)
        if self.compliance.is_clean(text):
            return text.strip()
        text2 = await self.ai.complete(NEUTRAL_SYSTEM, user + _REWRITE_HINT)
        if self.compliance.is_clean(text2):
            return text2.strip()
        return _strip_violating_sentences(text2, self.compliance)

    async def generate_market_view(self, item_views: list[str]) -> str:
        if not item_views:
            return ""
        text = await self.ai.complete(MARKET_VIEW_SYSTEM, build_market_view_user(item_views))
        if self.compliance.is_clean(text):
            return text.strip()
        return _strip_violating_sentences(text, self.compliance)


def _strip_violating_sentences(text: str, compliance) -> str:
    parts = re.split(r"(?<=[。.!?])\s*", text)
    kept = [p for p in parts if p and compliance.is_clean(p)]
    return " ".join(kept).strip() or "（本条因合规过滤暂无中性观点）"
```

- [ ] **Step 4: 实现 `src/view/brief_assembler.py`**

```python
"""组装当期 brief：选高分 story → 生成 view → 落库 + 综合观点。"""
from __future__ import annotations
from datetime import datetime, timezone
from ..db.rows import BriefRow, BriefItemRow


class BriefAssembler:
    def __init__(self, story_repo, score_repo, member_repo, raw_item_repo,
                 brief_repo, brief_item_repo, view_generator):
        self.stories = story_repo
        self.scores = score_repo
        self.members = member_repo
        self.raw = raw_item_repo
        self.briefs = brief_repo
        self.items = brief_item_repo
        self.view = view_generator

    async def build(self, period_type: str, period_date: str, *,
                    min_score: float = 6.0, max_items: int = 20,
                    language: str = "zh") -> int:
        now = datetime.now(timezone.utc).isoformat()
        scored = self._top_stories(min_score, max_items)
        brief_id = self.briefs.create(BriefRow(
            period_type=period_type, period_date=period_date, language=language,
            model="deepseek-chat", generated_at=now, status="draft"))
        item_views = []
        for rank, (story_id, _score) in enumerate(scored, start=1):
            primary = self._primary_raw_item(story_id)
            title = primary.title if primary else ""
            summary = primary.summary if primary else ""
            view = await self.view.generate_item_view(story_id, title, summary)
            item_views.append(view)
            self.items.add(BriefItemRow(
                brief_id=brief_id, story_id=story_id, rank=rank,
                headline=title, summary=summary, view_text=view, created_at=now))
        market_view = await self.view.generate_market_view(item_views)
        self.briefs.set_market_view(brief_id, market_view)
        return brief_id

    def _top_stories(self, min_score: float, max_items: int):
        ranked = []
        for s in self.stories.recent("0000"):
            sc = self.scores.latest_for_story(s.id)
            if sc and sc.score >= min_score:
                ranked.append((s.id, sc.score))
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked[:max_items]

    def _primary_raw_item(self, story_id: int):
        ids = self.members.raw_items_for_story(story_id)
        return self.raw.get(ids[0]) if ids else None
```

- [ ] **Step 5: 跑测试确认通过** — `pytest tests/view/ -v`
- [ ] **Step 6: 提交** — `git commit -m "feat(view): ViewGenerator + BriefAssembler with compliance enforcement"`

---

## 自检
- 覆盖设计文档第 5 步（中性 view + 综合市场观点）、第 8 节（skill 路由矩阵 + 合规过滤）。✔
- 提示词模板逐一提炼自 morning-note/earnings-analysis/sector-overview/thematic，且明确剥离方向性结论。✔
- 合规：system 硬约束 + 输出层 ComplianceChecker 扫描 + 命中重写 + 仍不洁则降级剥离。✔
- 接口 `ViewGenerator.generate_item_view/generate_market_view`、`ComplianceChecker.scan`、`BriefAssembler.build` 与索引一致。✔
- 免责声明在子计划 6 渲染层加（每期固定附）。
