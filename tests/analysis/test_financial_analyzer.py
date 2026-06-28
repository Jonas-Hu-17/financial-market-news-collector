"""Task 2: FinancialAnalyzer 测试（用假 AI 客户端，不下模型）。"""
import asyncio
import json
from src.db import init_db
from src.db.repositories.taxonomy_repo import TaxonomyRepo
from src.analysis.financial_analyzer import FinancialAnalyzer


class FakeAI:
    def __init__(self, payload):
        self.payload = payload

    async def complete(self, system, user):
        return self.payload


def test_analyze_parses_result(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    payload = json.dumps({
        "score": 8.5,
        "rationale": "large cross-border M&A",
        "tags": {
            "market_type": "secondary",
            "industry_group": "TMT",
            "product_group": "MA",
            "region": "GreaterChina",
            "asset_class": "Equity",
        },
        "entities": [
            {"type": "company", "name": "Acme", "ticker": None, "role": "primary"}
        ],
    })
    fa = FinancialAnalyzer(FakeAI(payload), TaxonomyRepo(db))
    res = asyncio.run(fa.analyze("Acme buys Beta", "deal"))
    assert res.score == 8.5
    assert res.tag_codes["product_group"] == "MA"
    assert res.entities[0]["name"] == "Acme"


def test_analyze_handles_bad_json(tmp_path):
    db = init_db(str(tmp_path / "t.db"))
    fa = FinancialAnalyzer(FakeAI("not json"), TaxonomyRepo(db))
    assert asyncio.run(fa.analyze("x", "y")) is None
