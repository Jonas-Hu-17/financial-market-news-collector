"""Task 5: 金融 RSS 源配置测试 — 读取 config.example.json，验证金融源。"""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "config.example.json"


def test_config_has_financial_rss_sources():
    cfg = json.loads(CONFIG_PATH.read_text())
    rss_sources = cfg["sources"]["rss"]
    urls = {s["url"] for s in rss_sources}
    names = {s["name"] for s in rss_sources}

    # 验证包含金融源域名特征
    assert any("reuters" in u.lower() for u in urls), "Reuters source missing"
    assert any("ft.com" in u for u in urls) or any("financial" in u.lower() for u in urls), "FT source missing"
    assert any("cnbc" in u.lower() for u in urls), "CNBC source missing"
    assert any("marketwatch" in u.lower() for u in urls), "MarketWatch source missing"
    assert any("scmp" in u.lower() for u in urls), "SCMP source missing"
    assert any("nikkei" in u.lower() for u in urls) or any("asia.nikkei" in u.lower() for u in urls), "Nikkei source missing"

    # 验证每条都有 name/url/enabled
    for s in rss_sources:
        assert "name" in s, f"Missing 'name' in {s}"
        assert "url" in s, f"Missing 'url' in {s}"
        assert "enabled" in s, f"Missing 'enabled' in {s}"
