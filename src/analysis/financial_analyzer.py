"""一次 LLM 调用产出 金融重要性分 + 五轴分类 + 实体。"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Optional
from ..ai.financial_prompts import (
    FINANCIAL_SCORE_SYSTEM, FINANCIAL_SCORE_BATCH_SYSTEM,
    build_score_user, build_batch_score_user,
)

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

    async def analyze_batch(
        self, items: list[tuple[str, str]]
    ) -> dict[str, "AnalysisResult"]:
        """批量打分：一次调用处理多条。返回 {story_key: AnalysisResult}。

        items: [(story_key, summary), ...] 其中 story_key 由调用方映射，
        解析失败返回空 dict，不抛异常。
        """
        if not items:
            return {}
        try:
            user = build_batch_score_user(items, self._allowed_codes())
            raw = await self.ai.complete(FINANCIAL_SCORE_BATCH_SYSTEM, user)
            data = json.loads(_strip_fences(raw))
            if not isinstance(data, list):
                return {}
            results: dict[str, "AnalysisResult"] = {}
            for entry in data:
                idx = entry.get("idx")
                if idx is None or idx < 0 or idx >= len(items):
                    continue
                key = items[idx][0]
                results[key] = AnalysisResult(
                    score=float(entry["score"]),
                    rationale=entry.get("rationale", ""),
                    tag_codes={
                        d: (entry.get("tags", {}) or {}).get(d)
                        for d in _DIMENSIONS
                    },
                    entities=entry.get("entities", []) or [],
                )
            return results
        except Exception:
            return {}


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    return t.strip()
