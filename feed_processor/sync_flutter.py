"""
SoloForge AI
Flutter Sync

Sprint 45.5
Production Version

Sync Discovery Database
→ Flutter Assets
"""

import argparse
import shutil
from pathlib import Path

# ==========================================================
# Config
# ==========================================================

ROOT = Path(__file__).resolve().parent.parent

DISCOVERY_DIR = ROOT / "data" / "discovery"

FLUTTER_DATA = (
    ROOT
    / "frontend"
    / "assets"
    / "data"
)

SOURCE_CATEGORY_INDEX = (
    DISCOVERY_DIR
    / "category_index.json"
)

SOURCE_CHUNK_INDEX = (
    DISCOVERY_DIR
    / "chunk_index.json"
)

SOURCE_REPORT = (
    DISCOVERY_DIR
    / "discovery_report.json"
)

SOURCE_TOP_PRODUCTS = (
    DISCOVERY_DIR
    / "top_products.json"
)

SOURCE_CATEGORIES = (
    DISCOVERY_DIR
    / "categories"
)

TARGET_CATEGORY_INDEX = (
    FLUTTER_DATA
    / "category_index.json"
)

TARGET_CHUNK_INDEX = (
    FLUTTER_DATA
    / "chunk_index.json"
)

TARGET_REPORT = (
    FLUTTER_DATA
    / "discovery_report.json"
)

TARGET_TOP_PRODUCTS = (
    FLUTTER_DATA
    / "top_products.json"
)

TARGET_CATEGORIES = (
    FLUTTER_DATA
    / "categories"
)

# ==========================================================
# Copy File
# ==========================================================


def copy_file(source: Path, target: Path):

    if not source.exists():
        print(f"Missing : {source}")
        return False

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        target,
    )

    print(f"Copied : {target.name}")

    return True


# ==========================================================
# Copy Chunk Database
# ==========================================================


def copy_categories():

    if not SOURCE_CATEGORIES.exists():

        print("Missing : categories")

        return (
            0,
            0,
        )

    if TARGET_CATEGORIES.exists():

        shutil.rmtree(
            TARGET_CATEGORIES
        )

    TARGET_CATEGORIES.mkdir(
        parents=True,
        exist_ok=True,
    )

    category_count = 0
    chunk_count = 0

    for category_dir in sorted(
        SOURCE_CATEGORIES.iterdir()
    ):

        if not category_dir.is_dir():
            continue

        target_dir = (
            TARGET_CATEGORIES
            / category_dir.name
        )

        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        category_count += 1

        for chunk in sorted(
            category_dir.glob(
                "chunk_*.json"
            )
        ):

            shutil.copy2(
                chunk,
                target_dir / chunk.name,
            )

            print(
                f"Copied : "
                f"{category_dir.name}/"
                f"{chunk.name}"
            )

            chunk_count += 1

    return (
        category_count,
        chunk_count,
    )


# ==========================================================
# Sync
# ==========================================================


def sync(
    full=False,
):

    print("=" * 60)
    print("Flutter Discovery Sync")
    print("=" * 60)

    print(
        f"Mode : {'Full' if full else 'Production'}"
    )

    print()

    copy_file(
        SOURCE_CATEGORY_INDEX,
        TARGET_CATEGORY_INDEX,
    )

    copy_file(
        SOURCE_CHUNK_INDEX,
        TARGET_CHUNK_INDEX,
    )

    copy_file(
        SOURCE_REPORT,
        TARGET_REPORT,
    )

    if full:

        print()

        print("Full Mode")

        copy_file(
            SOURCE_TOP_PRODUCTS,
            TARGET_TOP_PRODUCTS,
        )

    print()

    (
        category_count,
        chunk_count,
    ) = copy_categories()

    print()

    print("=" * 60)
    print("Flutter Sync Complete")
    print("=" * 60)

    print(
        f"Categories Copied : {category_count}"
    )

    print(
        f"Chunks Copied     : {chunk_count}"
    )

    print()

    print(
        f"Output : {FLUTTER_DATA}"
    )

    print("=" * 60)


# ==========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--full",
        action="store_true",
        help="Sync top_products.json",
    )

    args = parser.parse_args()

    sync(
        full=args.full,
    )