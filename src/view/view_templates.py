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
- Be concise (2-4 sentences for each field). Write in the user's language (Chinese \
unless item is clearly English-only context).
- If facts are unverified, say so.

OUTPUT FORMAT: Return a single JSON object with exactly two fields:
- "summary": one objective sentence describing what happened (the news itself, \
NOT its impact).
- "view": a neutral impact statement as described above.
Both must be in the user's language and must NOT contain any investment advice.

IMPORTANT: The "view" field must contain ONLY the neutral impact text itself — no \
heading, no prefix, no labels like "中性影响说明" or "Neutral Impact Note". Do not \
start with a title. Just write the impact content directly."""

# 每个模板提炼自对应 skill 的分析骨架（去掉方向性输出）
_MA = """A merger / acquisition / deal item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing what happened — this is the \
"summary" field.
Then, write a neutral impact note covering (framework distilled from competitive-analysis \
& comps):
- Strategic rationale / fit implied by the deal (what capability or market it adds)
- Parties and their roles; deal consideration or implied multiple if stated
- Which valuation drivers (synergies, market structure, competitive dynamics) it touches
Do NOT judge whether it is good/bad for any stock.
Return JSON: {{"summary": "...", "view": "..."}}"""

_EARNINGS = """An earnings / results item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing what was reported — this is \
the "summary" field.
Then, write a neutral impact note (framework distilled from earnings-analysis \
Parse→Compare→Diagnose):
- What was reported vs. prior period/expectations (beat/miss/in-line if stated)
- Which operational drivers changed (revenue mix, margins, guidance)
- What it signals about the forward operating trajectory
Stop at diagnosis — do NOT give a buy/sell verdict or price target.
Return JSON: {{"summary": "...", "view": "..."}}"""

_SECTOR = """A sector / macro / policy item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing the event — this is the \
"summary" field.
Then, write a neutral impact note (framework distilled from sector-overview):
- The sector/macro development and its driver
- Which parts of the value chain or which market segments it touches
- Possible second-order effects on demand, costs, or valuation multiples (as possibilities)
Do NOT recommend positioning.
Return JSON: {{"summary": "...", "view": "..."}}"""

_THEMATIC = """A thematic / secular-trend item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing the trend/development — this \
is the "summary" field.
Then, write a neutral impact note (framework distilled from thematic-investment-research \
DRIVER lens):
- The structural driver and whether it appears durable vs. temporary
- Who the beneficiaries / exposed parties are along the value chain
- Which leading indicators would confirm or refute the trend
Do NOT make a directional investment call.
Return JSON: {{"summary": "...", "view": "..."}}"""

_PRIMARY = """A primary-market (PE/VC) financing item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing the deal — this is the \
"summary" field.
Then, write a neutral impact note:
- Round/stage, amount, and parties (investors / company) if stated
- What it implies about the sector's funding environment and the company's stage
- Read-across to comparable private/public names (as factual context only)
Do NOT give an investment recommendation.
Return JSON: {{"summary": "...", "view": "..."}}"""

_DEFAULT = """A financial markets news item.
TITLE: {title}
SUMMARY: {summary}
CONTEXT: {context}

First, write one objective sentence (in Chinese) describing the news — this is the \
"summary" field.
Then, write a neutral 2-4 sentence impact note: what it is, which parties/markets it \
touches, and which valuation or market-mechanic drivers could be affected (as \
possibilities). No advice, no direction, no price target.
Return JSON: {{"summary": "...", "view": "..."}}"""

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
