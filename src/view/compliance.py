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
