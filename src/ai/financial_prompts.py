"""金融市场重要性打分 + 五轴分类 + 实体抽取的提示词。"""
from __future__ import annotations
import json

FINANCIAL_SCORE_SYSTEM = """You are a financial markets news triage analyst. \
Score each item 0-10 by its importance to markets and asset valuation, classify it, \
and extract the entities (companies/instruments) involved.

Scoring guide (importance to markets & valuation):
- 9-10: Market-moving — major M&A, central bank policy shifts, large IPOs, systemic events
- 7-8:  High — notable deals/financings, earnings surprises, guidance changes, regulation
- 5-6:  Relevant — sector developments, mid-size raises, management changes
- 3-4:  Low — routine updates, minor filings
- 0-2:  Noise — promotional, off-topic, trivial

This is a NEUTRAL triage step: do NOT give buy/sell opinions or price targets. \
Only score, classify, and extract. Respond with VALID JSON only."""


def build_score_user(title: str, summary: str, taxonomy_codes: dict[str, list[str]]) -> str:
    codes = json.dumps(taxonomy_codes, ensure_ascii=False)
    return f"""News item:
TITLE: {title}
SUMMARY: {summary or "(none)"}

Allowed classification codes (choose only from these; a dimension may be null if unclear):
{codes}

Return JSON exactly:
{{
  "score": <float 0-10>,
  "rationale": "<one neutral sentence on why it matters to markets>",
  "tags": {{
    "market_type": "<code or null>",
    "industry_group": "<code or null>",
    "product_group": "<code or null>",
    "region": "<code or null>",
    "asset_class": "<code or null>"
  }},
  "entities": [{{"type": "company|ticker|sector|person", "name": "<name>", "ticker": "<or null>", "role": "primary|related"}}]
}}"""
