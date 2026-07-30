"""
SoloForge AI
Matched Catalog Exporter

Export only products that have
Affiliate Link from Master Catalog.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "catalog_matched.json"
)


class MatchedExporter:

    def __init__(self):

        self.products = []

    # --------------------------------------------------

    @property
    def count(self):

        return len(self.products)

    # --------------------------------------------------

    def add(self, product):

        links = product.get("links", {})

        affiliate = str(
            links.get("affiliate", "")
        ).strip()

        # ไม่มี Affiliate Link ไม่ต้อง Export
        if not affiliate:
            return

        self.products.append(product)

    # --------------------------------------------------

    def write(self):

        # เรียงคะแนนจากมากไปน้อย
        self.products.sort(
            key=lambda p: p.get(
                "miniBossScore",
                0
            ),
            reverse=True,
        )

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                self.products,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print("=" * 60)
        print(
            f"Matched Catalog Exported : {self.count:,} products"
        )
        print(
            f"Output File : {OUTPUT_FILE}"
        )
        print("=" * 60)