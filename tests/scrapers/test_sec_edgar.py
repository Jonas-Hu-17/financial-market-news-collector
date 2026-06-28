"""Task 3: SEC EDGAR scraper 离线解析测试。"""
import asyncio
import httpx
from src.scrapers.sec_edgar import parse_edgar_atom

SAMPLE = """<?xml version='1.0'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
 <entry><title>8-K - ACME CORP (0000123)</title>
  <link href='https://www.sec.gov/x/8k.htm'/>
  <updated>2026-06-28T10:00:00-04:00</updated>
  <summary>Item 1.01 Entry into a Material Definitive Agreement</summary>
 </entry></feed>"""


def test_parse_edgar_atom():
    items = parse_edgar_atom(SAMPLE, form_type="8-K")
    assert len(items) == 1
    assert items[0].title.startswith("8-K")
    assert str(items[0].url).endswith("8k.htm")
