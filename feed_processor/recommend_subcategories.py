"""
SoloForge AI
Recommend Subcategories

Sprint 44

Generate enabled_subcategories.json

Input

- category_statistics.json
- blacklist_subcategories.json

Output

- enabled_subcategories.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DISCOVERY_DIR = ROOT / "data" / "discovery"
CONFIG_DIR = ROOT / "config"

CATEGORY_FILE = (
    DISCOVERY_DIR
    / "category_statistics.json"
)

BLACKLIST_FILE = (
    CONFIG_DIR
    / "blacklist_subcategories.json"
)

OUTPUT_FILE = (
    CONFIG_DIR
    / "enabled_subcategories.json"
)


def load_blacklist():

    if not BLACKLIST_FILE.exists():
        return {}

    with open(
        BLACKLIST_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def main():

    with open(
        CATEGORY_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        stats = json.load(f)

    blacklist = load_blacklist()

    categories = {}

    all_categories = stats.get(
        "all_categories",
        {}
    )

    for category in all_categories.keys():

        levels = [
            x.strip()
            for x in category.split(">")
        ]

        if len(levels) < 2:
            continue

        level1 = levels[0]
        level2 = levels[1]

        categories.setdefault(
            level1,
            {}
        )

        enabled = True

        if (
            level1 in blacklist
            and
            level2 in blacklist[level1]
        ):

            enabled = False

        categories[level1][level2] = enabled

    CONFIG_DIR.mkdir(
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

    level1_count = len(categories)

    level2_count = sum(
        len(v)
        for v in categories.values()
    )

    enabled_count = sum(
        1
        for subs in categories.values()
        for enabled in subs.values()
        if enabled
    )

    disabled_count = sum(
        1
        for subs in categories.values()
        for enabled in subs.values()
        if not enabled
    )

    print("=" * 60)
    print("Recommend Subcategories Complete")
    print("=" * 60)
    print(f"Level 1 Categories : {level1_count}")
    print(f"Level 2 Categories : {level2_count}")
    print(f"Enabled            : {enabled_count}")
    print(f"Disabled           : {disabled_count}")
    print(f"Blacklist File     : {BLACKLIST_FILE}")
    print(f"Output             : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()