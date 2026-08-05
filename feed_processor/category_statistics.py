"""
SoloForge AI
Category Statistics

Sprint 43

Analyze all product categories from ranked JSONL files.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "data" / "discovery"

CSV_FILE = OUTPUT_DIR / "category_statistics.csv"
JSON_FILE = OUTPUT_DIR / "category_statistics.json"
TREE_FILE = OUTPUT_DIR / "category_tree.json"


def iter_products():
    """Stream products from ranked JSONL files."""

    files = sorted(INPUT_DIR.glob("ranked_products_*.jsonl"))

    print("=" * 60)
    print(f"Found {len(files)} JSONL files")
    print("=" * 60)

    for file in files:

        print(f"Reading {file.name}")

        with open(file, "r", encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def add_to_tree(tree, levels):

    node = tree

    for level in levels:

        if level not in node:

            node[level] = {
                "count": 0,
                "children": {}
            }

        node[level]["count"] += 1

        node = node[level]["children"]


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    category_counter = defaultdict(int)
    level1_counter = defaultdict(int)
    level2_counter = defaultdict(int)
    level3_counter = defaultdict(int)

    category_tree = {}

    processed = 0

    for product in iter_products():

        processed += 1

        category = (
            product.get("category")
            or "Uncategorized"
        )

        category_counter[category] += 1

        levels = [
            x.strip()
            for x in category.split(">")
        ]

        add_to_tree(category_tree, levels)

        if len(levels) >= 1:
            level1_counter[levels[0]] += 1

        if len(levels) >= 2:
            level2_counter[
                f"{levels[0]} > {levels[1]}"
            ] += 1

        if len(levels) >= 3:
            level3_counter[
                f"{levels[0]} > {levels[1]} > {levels[2]}"
            ] += 1

        if processed % 100000 == 0:

            print(f"Processed : {processed:,}")

    # ---------------- CSV ----------------

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "Category",
            "Products",
        ])

        for category, count in sorted(
            category_counter.items(),
            key=lambda x: x[1],
            reverse=True,
        ):

            writer.writerow([
                category,
                count,
            ])

    # ---------------- JSON ----------------

    summary = {

        "processed_products": processed,

        "unique_categories": len(category_counter),

        "level1": dict(
            sorted(
                level1_counter.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

        "level2": dict(
            sorted(
                level2_counter.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

        "level3": dict(
            sorted(
                level3_counter.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

        "all_categories": dict(
            sorted(
                category_counter.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),

    }

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    with open(
        TREE_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            category_tree,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 60)
    print("Category Statistics Complete")
    print("=" * 60)
    print(f"Products           : {processed:,}")
    print(f"Unique Categories  : {len(category_counter)}")
    print(f"Level 1 Categories : {len(level1_counter)}")
    print(f"Level 2 Categories : {len(level2_counter)}")
    print(f"Level 3 Categories : {len(level3_counter)}")
    print()
    print(f"CSV  : {CSV_FILE}")
    print(f"JSON : {JSON_FILE}")
    print(f"TREE : {TREE_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()