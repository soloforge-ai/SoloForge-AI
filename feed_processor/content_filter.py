"""
SoloForge AI
Content Filter

Sprint 44
Production Version

Rule-based product filter.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = (
    ROOT
    / "config"
    / "content_filter_rules.json"
)


class ContentFilter:

    def __init__(self):

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            self.rules = json.load(f)

        self.reset()

    # --------------------------------------------------

    def reset(self):

        self.stats = {
            "accepted": 0,
            "title": 0,
            "description": 0,
            "price": 0,
            "affiliate": 0,
            "stock": 0,
            "commission": 0,
        }

    # --------------------------------------------------

    def _contains(self, text, keywords):

        text = (text or "").lower()

        for keyword in keywords:

            if keyword.lower() in text:
                return True

        return False

    # --------------------------------------------------

    def accept(self, product):

        title = product.get("title", "")

        description = product.get(
            "description",
            "",
        )

        # ----------------------------------------------
        # Title
        # ----------------------------------------------

        if self._contains(
            title,
            self.rules["title_blacklist"],
        ):
            self.stats["title"] += 1
            return False

        # ----------------------------------------------
        # Description
        # ----------------------------------------------

        if self._contains(
            description,
            self.rules["description_blacklist"],
        ):
            self.stats["description"] += 1
            return False

        # ----------------------------------------------
        # Price
        # ----------------------------------------------

        price = (
            product.get("sale_price")
            or product.get("price")
            or 0
        )

        if price < self.rules["min_price"]:
            self.stats["price"] += 1
            return False

        if price > self.rules["max_price"]:
            self.stats["price"] += 1
            return False

        # ----------------------------------------------
        # Affiliate
        # ----------------------------------------------

        if self.rules["require_affiliate"]:

            affiliate = (
                product.get("links", {})
                .get("affiliate", "")
            )

            if not affiliate:
                self.stats["affiliate"] += 1
                return False

        # ----------------------------------------------
        # Stock
        # ----------------------------------------------

        if self.rules["reject_zero_stock"]:

            if product.get("stock", 0) <= 0:
                self.stats["stock"] += 1
                return False

        # ----------------------------------------------
        # Commission
        # ----------------------------------------------

        if self.rules["reject_zero_commission"]:

            commission = (
                product.get(
                    "commission",
                    {},
                ).get(
                    "rate",
                    0,
                )
            )

            if commission <= 0:
                self.stats["commission"] += 1
                return False

        # ----------------------------------------------
        # Accepted
        # ----------------------------------------------

        self.stats["accepted"] += 1

        return True

    # --------------------------------------------------

    def get_statistics(self):

        rejected = (
            self.stats["title"]
            + self.stats["description"]
            + self.stats["price"]
            + self.stats["affiliate"]
            + self.stats["stock"]
            + self.stats["commission"]
        )

        return {
            **self.stats,
            "rejected": rejected,
        }

    # --------------------------------------------------

    def print_statistics(self):

        stats = self.get_statistics()

        print()
        print("=" * 60)
        print("Content Filter Statistics")
        print("=" * 60)

        print(f"Rejected by Title       : {stats['title']:,}")
        print(f"Rejected by Description : {stats['description']:,}")
        print(f"Rejected by Price       : {stats['price']:,}")
        print(f"Rejected by Affiliate   : {stats['affiliate']:,}")
        print(f"Rejected by Stock       : {stats['stock']:,}")
        print(f"Rejected by Commission  : {stats['commission']:,}")

        print("-" * 60)

        print(f"Rejected Total          : {stats['rejected']:,}")
        print(f"Accepted                : {stats['accepted']:,}")

        print("=" * 60)