"""
SoloForge AI
Statistics Collector
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


class StatisticsCollector:

    def __init__(self):

        self.total_products = 0

        self.total_price = 0.0
        self.total_rating = 0.0

        self.official_shop = 0
        self.preferred_shop = 0

        self.category_counter = Counter()
        self.brand_counter = Counter()

    def add(self, product):

        self.total_products += 1

        self.total_price += product.get("price", 0)
        self.total_rating += product.get("rating", 0)

        shop = product.get("shop", {})

        if shop.get("official", False):
            self.official_shop += 1

        if shop.get("preferred", False):
            self.preferred_shop += 1

        category = product.get("category", "").strip()

        if category:
            self.category_counter[category] += 1

        brand = product.get("brand", "").strip()

        if not brand:
            brand = "No Brand"

        self.brand_counter[brand] += 1

    def write(self):

        if self.total_products == 0:
            average_price = 0
            average_rating = 0
        else:
            average_price = round(
                self.total_price / self.total_products,
                2,
            )

            average_rating = round(
                self.total_rating / self.total_products,
                2,
            )

        stats = {

            "version": 1,

            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),

            "total_products": self.total_products,

            "official_shop": self.official_shop,

            "preferred_shop": self.preferred_shop,

            "average_price": average_price,

            "average_rating": average_rating,

            "top_categories":
                dict(
                    self.category_counter.most_common(20)
                ),

            "top_brands":
                dict(
                    self.brand_counter.most_common(20)
                ),
        }

        output = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "processed"
            / "stats.json"
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            output,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                stats,
                f,
                ensure_ascii=False,
                indent=4,
            )