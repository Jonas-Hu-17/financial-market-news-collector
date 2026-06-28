"""Task 1: 中性 view 提示词模板测试。"""
from src.view.view_templates import NEUTRAL_SYSTEM, TEMPLATES, MARKET_VIEW_SYSTEM


def test_system_enforces_neutrality():
    s = NEUTRAL_SYSTEM.lower()
    assert "not" in s and "advice" in s
    assert "neutral" in s


def test_templates_cover_routes():
    for k in ["ma", "earnings", "sector_macro", "thematic",
              "primary_market", "default"]:
        assert k in TEMPLATES
        assert "{title}" in TEMPLATES[k]


def test_ma_template_has_skill_dimensions():
    # 提炼自 competitive-analysis/comps：战略契合、对价/倍数、相关方
    t = TEMPLATES["ma"]
    assert "strategic" in t.lower() or "战略" in t
