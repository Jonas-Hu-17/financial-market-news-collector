"""一次 LLM 调用产出 金融重要性分 + 五轴分类 + 实体。"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Optional
from ..ai.financial_prompts import FINANCIAL_SCORE_SYSTEM, build_score_user

_DIMENSIONS = ["market_type", "industry_group", "product_group", "region", "asset_class"]


@dataclass
class AnalysisResult:
    score: float
    rationale: str
    tag_codes: dict
    entities: list


class FinancialAnalyzer:
    def __init__(self, ai_client, taxonomy_repo):
        self.ai = ai_client
        self.tax = taxonomy_repo

    def _allowed_codes(self) -> dict[str, list[str]]:
        return {d: [t.code for t in self.tax.list_by_dimension(d)] for d in _DIMENSIONS}

    async def analyze(self, title: str, summary: str) -> Optional[AnalysisResult]:
        user = build_score_user(title, summary, self._allowed_codes())
        try:
            raw = await self.ai.complete(FINANCIAL_SCORE_SYSTEM, user)
            data = json.loads(_strip_fences(raw))
            return AnalysisResult(
                score=float(data["score"]),
                rationale=data.get("rationale", ""),
                tag_codes={d: (data.get("tags", {}) or {}).get(d) for d in _DIMENSIONS},
                entities=data.get("entities", []) or [],
            )
        except Exception:
            return None


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    return t.strip()
