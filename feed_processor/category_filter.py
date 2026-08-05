"""
SoloForge AI
Category Filter

Sprint 44

Filter products by
- Level 1 Category
- Level 2 Subcategory
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CATEGORY_FILE = (
    ROOT
    / "config"
    / "enabled_categories.json"
)

SUBCATEGORY_FILE = (
    ROOT
    / "config"
    / "enabled_subcategories.json"
)


class CategoryFilter:

    def __init__(self):

        # --------------------------
        # Level 1
        # --------------------------

        with open(
            CATEGORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            config = json.load(f)

        self.enabled_categories = set(
            config.get("include", [])
        )

        # --------------------------
        # Level 2
        # --------------------------

        with open(
            SUBCATEGORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            self.enabled_subcategories = json.load(f)

    # --------------------------------------------------

    def accept(self, product):

        category = (
            product.get("category")
            or ""
        ).strip()

        if not category:
            return False

        levels = [
            x.strip()
            for x in category.split(">")
        ]

        # --------------------------
        # Level 1
        # --------------------------

        if len(levels) < 1:
            return False

        level1 = levels[0]

        if level1 not in self.enabled_categories:
            return False

        # --------------------------
        # ไม่มี Level 2
        # --------------------------

        if len(levels) < 2:
            return True

        level2 = levels[1]

        allowed = self.enabled_subcategories.get(
            level1
        )

        if allowed is None:
            return False

        # --------------------------
        # รองรับ 2 รูปแบบ
        #
        # {
        #   "Beauty":[...]
        # }
        #
        # หรือ
        #
        # {
        #   "Beauty":{
        #      "Skincare":true
        #   }
        # }
        # --------------------------

        if isinstance(allowed, list):

            return level2 in allowed

        if isinstance(allowed, dict):

            return allowed.get(
                level2,
                False,
            )

        return False