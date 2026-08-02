import json
from pathlib import Path

# ==========================
# Config
# ==========================

ROOT = Path(__file__).resolve().parent.parent

SOURCE = (
    ROOT
    / "data"
    / "processed"
    / "catalog_matched.json"
)

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

FEATURED_LIMIT = 200

# ==========================
# Sync
# ==========================


def sync():

    print("=" * 60)
    print("Loading Matched Catalog...")
    print("=" * 60)

    if not SOURCE.exists():
        print(f"ERROR : {SOURCE} not found.")
        return

    with open(
        SOURCE,
        "r",
        encoding="utf-8",
    ) as f:

        products = json.load(f)

    featured_products = sorted(
        products,
        key=lambda x: x.get("miniBossScore", 0),
        reverse=True,
    )[:FEATURED_LIMIT]

    CATALOG_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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