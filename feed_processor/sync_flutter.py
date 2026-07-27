import json
from pathlib import Path

from config import OUTPUT_DIR

# ==========================
# Config
# ==========================

TOP_PRODUCTS = 1000
FEATURED_LIMIT = 200

ROOT = Path(__file__).resolve().parent.parent

CATALOG_OUTPUT = (
    ROOT
    / "frontend"
    / "assets"
    / "data"
    / "catalog.json"
)

FEATURED_OUTPUT = (
    ROOT
    / "frontend"
    / "assets"
    / "data"
    / "featured_catalog.json"
)

# ==========================
# Sync
# ==========================


def sync():

    products = []

    jsonl_files = sorted(
        OUTPUT_DIR.glob("ranked_products_*.jsonl")
    )

    for file in jsonl_files:

        with open(
            file,
            "r",
            encoding="utf-8",
        ) as f:

            for line in f:

                if not line.strip():
                    continue

                products.append(json.loads(line))

                if len(products) >= TOP_PRODUCTS:
                    break

        if len(products) >= TOP_PRODUCTS:
            break

    # ==========================
    # Sort Featured Products
    # ==========================

    featured_products = sorted(
        products,
        key=lambda x: x.get("miniBossScore", 0),
        reverse=True,
    )[:FEATURED_LIMIT]

    # ==========================
    # Create Output Folder
    # ==========================

    CATALOG_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ==========================
    # Save catalog.json
    # ==========================

    with open(
        CATALOG_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            products,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ==========================
    # Save featured_catalog.json
    # ==========================

    with open(
        FEATURED_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            featured_products,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ==========================
    # Log
    # ==========================

    print("=" * 60)
    print("Flutter Sync Complete")
    print("=" * 60)
    print(f"Catalog Products : {len(products):,}")
    print(f"Featured         : {len(featured_products):,}")
    print()
    print(f"Catalog Output   : {CATALOG_OUTPUT}")
    print(f"Featured Output  : {FEATURED_OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    sync()