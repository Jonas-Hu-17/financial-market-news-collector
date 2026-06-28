"""Task 4: HKEX 披露易公告 scraper 离线解析测试。"""
from src.scrapers.hkex import parse_hkex_json

SAMPLE = {"newslist": [
    {"NEWS_ID": "1", "TITLE": "DISCLOSEABLE TRANSACTION - Acquisition",
     "STOCK_CODE": "0700", "DATE_TIME": "2026-06-28 08:00",
     "FILE_LINK": "https://www1.hkexnews.hk/x.pdf"}
]}


def test_parse_hkex_json():
    items = parse_hkex_json(SAMPLE)
    assert len(items) == 1
    assert "Acquisition" in items[0].title
    assert str(items[0].url).endswith(".pdf")
