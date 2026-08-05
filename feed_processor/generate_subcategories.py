"""
SoloForge AI
Generate Enabled Subcategories

Sprint 44

Generate config/enabled_subcategories.json
from category_statistics.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    ROOT
    / "data"
    / "discovery"
    / "category_statistics.json"
)

OUTPUT_DIR = ROOT / "config"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "enabled_subcategories.json"
)


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        stats = json.load(f)

    categories = {}

    for category in stats["all_categories"]:

        levels = [
            x.strip()
            for x in category.split(">")
        ]

        if len(levels) < 2:
            continue

        level1 = levels[0]
        level2 = levels[1]

        if level1 not in categories:

            categories[level1] = {}

        categories[level1][level2] = True

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            categories,
            f,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )

    total_level1 = len(categories)

    total_level2 = sum(
        len(x)
        for x in categories.values()
    )

    print("=" * 60)
    print("Generate Subcategories Complete")
    print("=" * 60)
    print(f"Level 1 Categories : {total_level1}")
    print(f"Level 2 Categories : {total_level2}")
    print(f"Output             : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()