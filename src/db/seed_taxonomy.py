"""预置受控词表（设计文档第 5 节五轴）。"""
from __future__ import annotations
from .database import Database
from .repositories.taxonomy_repo import TaxonomyRepo
from .rows import TaxonomyRow

_SEED = {
    "market_type": [("primary", "一级市场"), ("secondary", "二级市场")],
    "industry_group": [
        ("TMT", "TMT"), ("Consumer", "Consumer & Retail"),
        ("Healthcare", "Healthcare"), ("Energy", "Energy & Natural Resources"),
        ("Industrials", "Industrials"), ("FIG", "Financial Institutions"),
        ("RealEstate", "Real Estate"),
    ],
    "product_group": [
        ("MA", "M&A / Advisory"), ("ECM", "ECM"), ("DCM", "DCM"),
        ("LevFin", "Leveraged Finance"), ("Restructuring", "Restructuring"),
        ("VC", "VC融资"), ("PEBuyout", "PE Buyout"),
        ("FundClosing", "基金募集"), ("PreIPO", "Pre-IPO"),
        ("PrivatePlacement", "私募配售"),
    ],
    "region": [
        ("NA", "北美"), ("EU", "欧洲"), ("GreaterChina", "大中华(含香港)"),
        ("JPKR", "日韩"), ("SEA_India", "东南亚·印度"),
        ("EM", "新兴市场"), ("Global", "全球·跨区域"),
    ],
    "asset_class": [
        ("Equity", "股票"), ("Credit", "债券"), ("PE", "私募股权"),
        ("FX", "外汇"), ("Commodity", "大宗商品"),
    ],
}


def seed_taxonomy(db: Database) -> int:
    repo = TaxonomyRepo(db)
    n = 0
    for dimension, items in _SEED.items():
        for order, (code, label) in enumerate(items):
            repo.upsert(TaxonomyRow(
                dimension=dimension, code=code, label=label, sort_order=order))
            n += 1
    return n
