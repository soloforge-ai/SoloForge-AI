"""
SoloForge AI
Category Exporter

Sprint 44

Export Discovery Database

Can be used in 2 ways

1.
from category_exporter import export_categories

2.
py category_exporter.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DISCOVERY_DIR = ROOT / "data" / "discovery"

INPUT_FILE = DISCOVERY_DIR / "top_products.json"

OUTPUT_DIR = DISCOVERY_DIR / "categories"

INDEX_FILE = DISCOVERY_DIR / "category_index.json"


# ----------------------------------------------------------
# Utils
# ----------------------------------------------------------

def safe_filename(name: str) -> str:
    """Convert category name to safe filename."""

    name = name.replace("&", "and")
    name = name.replace("/", "-")
    name = name.replace("\\", "-")

    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)

    return name


# ----------------------------------------------------------
# Export
# ----------------------------------------------------------

def export_categories(discovery: dict):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    level1_catalog = {}

    total_products = 0

    # ------------------------------------------------------
    # Merge Level 3 -> Level 1
    # ------------------------------------------------------

    for full_category, products in discovery.items():

        levels = [
            x.strip()
            for x in full_category.split(">")
        ]

        if not levels:
            continue

        level1 = levels[0]

        level2 = (
            levels[1]
            if len(levels) > 1
            else "Others"
        )

        if level1 not in level1_catalog:

            level1_catalog[level1] = {}

        level1_catalog[level1].setdefault(
            level2,
            []
        )

        level1_catalog[level1][level2].extend(
            products
        )

        total_products += len(products)

    # ------------------------------------------------------
    # Export JSON
    # ------------------------------------------------------

    category_index = {}

    exported = 0

    for level1, subcategories in sorted(
        level1_catalog.items()
    ):

        filename = safe_filename(level1)

        output_file = OUTPUT_DIR / f"{filename}.json"

        product_count = sum(
            len(items)
            for items in subcategories.values()
        )

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                subcategories,
                f,
                ensure_ascii=False,
                indent=2,
            )

        category_index[level1] = {

            "name": level1,

            "file": f"categories/{filename}.json",

            "subcategories": len(subcategories),

            "products": product_count,

        }

        exported += 1

    with open(
        INDEX_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            category_index,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 60)
    print("Category Export Complete")
    print("=" * 60)
    print(f"Level 1 Categories : {exported}")
    print(f"Products Exported  : {total_products:,}")
    print(f"Output Directory   : {OUTPUT_DIR}")
    print(f"Category Index     : {INDEX_FILE}")
    print("=" * 60)


# ----------------------------------------------------------
# Standalone
# ----------------------------------------------------------

def main():

    if not INPUT_FILE.exists():

        print("top_products.json not found")

        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        discovery = json.load(f)

    export_categories(discovery)


if __name__ == "__main__":
    main()