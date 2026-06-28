"""按 story 分类标签路由到 view 模板。"""
from __future__ import annotations

_PRIMARY_PRODUCTS = {"VC", "PEBuyout", "FundClosing", "PreIPO", "PrivatePlacement"}


class ViewRouter:
    def __init__(self, story_tag_repo, taxonomy_repo):
        self.tags = story_tag_repo
        self.tax = taxonomy_repo

    def _codes(self, story_id: int) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for tax_id in self.tags.taxonomy_ids_for_story(story_id):
            row = self._tax_by_id(tax_id)
            if row:
                out.setdefault(row.dimension, set()).add(row.code)
        return out

    def _tax_by_id(self, tax_id: int):
        for dim in ["market_type", "industry_group", "product_group",
                     "region", "asset_class"]:
            for r in self.tax.list_by_dimension(dim):
                if r.id == tax_id:
                    return r
        return None

    def route(self, story_id: int) -> str:
        c = self._codes(story_id)
        product = c.get("product_group", set())
        market = c.get("market_type", set())
        region = c.get("region", set())
        if "MA" in product:
            return "ma"
        if product & _PRIMARY_PRODUCTS or "primary" in market:
            return "primary_market"
        if {"ECM", "DCM", "LevFin", "Restructuring"} & product:
            return "sector_macro"
        if "Global" in region and not product:
            return "thematic"
        if region or c.get("industry_group"):
            return "sector_macro"
        return "default"
