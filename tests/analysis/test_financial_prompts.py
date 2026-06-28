"""Task 1: 金融打分+分类 prompt 测试。"""
from src.ai.financial_prompts import FINANCIAL_SCORE_SYSTEM, build_score_user


def test_system_prompt_is_market_oriented():
    s = FINANCIAL_SCORE_SYSTEM.lower()
    assert "market" in s
    # 中性原则：打分阶段不产出投资建议
    assert "json" in s


def test_user_prompt_injects_allowed_codes():
    u = build_score_user("Acme buys Beta", "deal", {
        "market_type": ["primary", "secondary"],
        "product_group": ["MA", "ECM"]})
    assert "MA" in u and "secondary" in u
    assert "Acme buys Beta" in u
