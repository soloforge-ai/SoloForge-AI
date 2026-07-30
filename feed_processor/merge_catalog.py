"""
SoloForge AI
Catalog Merge Engine

Merge Product Feed
+
Shopee Master Catalog
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MASTER_FILE = ROOT / "data" / "raw" / "Shopee_MasterCatalog.csv"


class CatalogMerger:

    def __init__(self):

        self.master = {}
        self.loaded = 0
        self.matched = 0

    # --------------------------------------------------
    # Load Master Catalog
    # --------------------------------------------------

    def load(self):

        print("=" * 60)
        print("Loading Shopee Master Catalog...")
        print("=" * 60)

        with open(
            MASTER_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                itemid = str(
                    row.get("รหัสสินค้า", "")
                ).strip()

                if not itemid:
                    continue

                self.master[itemid] = {

                    "commission": {

                        "rate": self._to_float(
                            row.get("CommissionRate")
                        ),

                        "amount": self._to_float(
                            row.get("CommissionAmount")
                        ),

                    },

                    "links": {

                        "product": row.get(
                            "ลิงก์สินค้า",
                            ""
                        ),

                        "affiliate": row.get(
                            "ลิงก์ข้อเสนอ",
                            ""
                        ),

                    },

                    "metrics": {

                        "price_display": row.get(
                            "PriceDisplay",
                            ""
                        ),

                        "sold_display": row.get(
                            "SoldDisplay",
                            ""
                        ),

                        "price_value": self._to_float(
                            row.get("PriceValue")
                        ),

                        "sold_value": self._to_float(
                            row.get("SoldValue")
                        ),

                    }

                }

                self.loaded += 1

        print(f"Loaded : {self.loaded:,} products")
        print("=" * 60)

    # --------------------------------------------------
    # Merge Product
    # --------------------------------------------------

    def merge(self, product):

        # รองรับทั้ง itemid และ id
        itemid = str(
            product.get("itemid")
            or product.get("id")
            or ""
        ).strip()

        extra = self.master.get(itemid)

        if extra:

            self.matched += 1

            product["commission"] = extra["commission"]

            product["links"]["product"] = extra["links"]["product"]
            product["links"]["affiliate"] = extra["links"]["affiliate"]

            product["metrics"] = extra["metrics"]

        else:

            product.setdefault(
                "commission",
                {
                    "rate": 0.0,
                    "amount": 0.0,
                }
            )

            product.setdefault(
                "metrics",
                {
                    "price_display": "",
                    "sold_display": "",
                    "price_value": 0.0,
                    "sold_value": 0.0,
                }
            )

            product.setdefault(
                "links",
                {}
            )

            product["links"].setdefault("product", "")
            product["links"].setdefault("affiliate", "")

        return product

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    def summary(self):

        print("=" * 60)
        print(f"Master Catalog : {self.loaded:,}")
        print(f"Matched        : {self.matched:,}")
        print("=" * 60)

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    @staticmethod
    def _to_float(value):

        if value is None:
            return 0.0

        value = str(value).replace(",", "").strip()

        if value == "":
            return 0.0

        try:
            return float(value)
        except ValueError:
            return 0.0