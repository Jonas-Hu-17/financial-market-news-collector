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

Prioritization (boost importance for investment-banking-relevant events):
- M&A / takeovers / asset sales, ECM (IPO/follow-on), DCM (bond issuance),
  leveraged finance, restructuring → treat as HIGH importance (typically 7-9).
- Private-market financings (VC rounds, PE buyouts, fund closings, pre-IPO,
  private placements) → HIGH importance (7-9).
- Sector/industry coverage developments (earnings with read-through, guidance,
  regulatory/antitrust, major product/capacity moves) → MEDIUM-HIGH (6-8).
- Pure geopolitics / general macro with no direct corporate or market mechanism
  → keep MODERATE unless it is clearly market-moving for specific assets.
Deals, financings, and sector developments should generally rank above generic
geopolitical headlines of similar prominence.

This is a NEUTRAL triage step: do NOT give buy/sell opinions or price targets. \
Only score, classify, and extract. Respond with VALID JSON only."""


FINANCIAL_SCORE_BATCH_SYSTEM = """You are a financial markets news triage analyst. \
Score each item 0-10 by its importance to markets and asset valuation, classify each, \
and extract each item's entities (companies/instruments).

Scoring guide (importance to markets & valuation):
- 9-10: Market-moving — major M&A, central bank policy shifts, large IPOs, systemic events
- 7-8:  High — notable deals/financings, earnings surprises, guidance changes, regulation
- 5-6:  Relevant — sector developments, mid-size raises, management changes
- 3-4:  Low — routine updates, minor filings
- 0-2:  Noise — promotional, off-topic, trivial

Prioritization:
- M&A / takeovers / asset sales, ECM (IPO/follow-on), DCM (bond issuance),
  leveraged finance, restructuring → HIGH (7-9).
- Private-market financings → HIGH (7-9).
- Sector/industry developments → MEDIUM-HIGH (6-8).

Respond with a JSON ARRAY only — one object per item, using the idx field to preserve order."""


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


def build_batch_score_user(
    items: list[tuple[str, str]], taxonomy_codes: dict[str, list[str]]
) -> str:
    codes = json.dumps(taxonomy_codes, ensure_ascii=False)
    lines = []
    for i, (title, summary) in enumerate(items):
        lines.append(f"Item {i}: TITLE: {title}")
        lines.append(f"  SUMMARY: {summary or '(none)'}")
        lines.append("")
    item_block = "\n".join(lines)

    return f"""Score the following {len(items)} news items.

Allowed classification codes (choose only from these; a dimension may be null if unclear):
{codes}

{item_block}
Return a JSON ARRAY with one object per item (idx field preserves order):

[
  {{
    "idx": 0,
    "score": <float 0-10>,
    "rationale": "<one neutral sentence>",
    "tags": {{
      "market_type": "<code or null>",
      "industry_group": "<code or null>",
      "product_group": "<code or null>",
      "region": "<code or null>",
      "asset_class": "<code or null>"
    }},
    "entities": [{{"type": "company|ticker|sector|person", "name": "<name>", "ticker": "<or null>", "role": "primary|related"}}]
  }},
  ...
]"""
