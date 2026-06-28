"""Task 3: ComplianceChecker 建议性措辞拦截测试。"""
from src.view.compliance import ComplianceChecker


def test_flags_directional_terms():
    c = ComplianceChecker()
    assert not c.is_clean("We recommend buying this stock, price target $50")
    assert not c.is_clean("建议买入，目标价 50 元")
    assert c.scan("看多该板块")


def test_neutral_passes():
    c = ComplianceChecker()
    assert c.is_clean("该交易可能影响行业竞争格局与相关方的估值要素。")
