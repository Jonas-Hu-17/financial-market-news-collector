"""语言强制：确保 NEUTRAL_SYSTEM 和 MARKET_VIEW_SYSTEM 提示词要求简体中文输出。"""
from src.view.view_templates import NEUTRAL_SYSTEM, MARKET_VIEW_SYSTEM


def test_neutral_system_forces_chinese():
    """NEUTRAL_SYSTEM 应包含简体中文 / Simplified Chinese 强制字样。"""
    assert "简体中文" in NEUTRAL_SYSTEM
    assert "Simplified Chinese" in NEUTRAL_SYSTEM


def test_market_view_system_forces_chinese():
    """MARKET_VIEW_SYSTEM 应包含简体中文强制字样。"""
    assert "简体中文" in MARKET_VIEW_SYSTEM
    assert "Simplified Chinese" in MARKET_VIEW_SYSTEM
