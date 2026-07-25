from collections import Counter

from ..models.project_intelligence import ProjectIntelligence


FEATURE_RULES = {
    "AI Content Generator": [
        "forge_page.dart",
        "content_engine.dart",
    ],
    "Image Generator": [
        "image_engine.dart",
        "image_test_page.dart",
    ],
    "Affiliate Catalog": [
        "catalog_service.dart",
        "affiliate_repository.dart",
    ],
    "Character System": [
        "character_engine.dart",
        "character_loader.dart",
    ],
    "Creative System": [
        "creative_engine.dart",
        "creative_loader.dart",
    ],
    "Scene System": [
        "scene_engine.dart",
        "scene_loader.dart",
    ],
    "Authentication": [
        "login_page.dart",
        "auth_service.dart",
    ],
    "Settings": [
        "settings_page.dart",
    ],
    "History": [
        "history_page.dart",
    ],
    "Export": [
        "export_service.dart",
    ],
}


IGNORE_DUPLICATES = {
    "__init__.py",
    "config.py",
    "README.md",
    "LICENSE",
    "PROJECT_INDEX.md",
}


class ProjectIntelligenceBuilder:

    def build(self, inventory):

        intelligence = ProjectIntelligence()

        names = {item.name for item in inventory}

        # ----------------------------
        # Feature Detection
        # ----------------------------

        for feature, required in FEATURE_RULES.items():

            found = sum(
                filename in names
                for filename in required
            )

            if found == len(required):

                intelligence.completed_features.append(
                    feature
                )

            elif found > 0:

                intelligence.in_progress_features.append(
                    feature
                )

            else:

                intelligence.missing_features.append(
                    feature
                )

        # ----------------------------
        # Duplicate filenames
        # ----------------------------

        counter = Counter(
            item.name
            for item in inventory
        )

        intelligence.duplicate_files = sorted([
            name
            for name, count in counter.items()
            if (
                count > 1
                and name not in IGNORE_DUPLICATES
            )
        ])

        # ----------------------------
        # Possible Orphan Files
        # ----------------------------

        for item in inventory:

            if item.extension != ".dart":
                continue

            if item.category in (
                "Documentation",
                "Model",
            ):
                continue

            # มีคนเรียกใช้
            if item.used_by:
                continue

            # ไฟล์นี้เรียกไฟล์อื่น
            if item.dependencies:
                continue

            intelligence.orphan_files.append(
                item.path.replace("\\", "/")
            )

        # ----------------------------
        # Recommendations
        # ----------------------------

        if intelligence.missing_features:

            intelligence.recommendations.append(
                "Implement missing features."
            )

        if intelligence.duplicate_files:

            intelligence.recommendations.append(
                "Review duplicate filenames."
            )

        if intelligence.orphan_files:

            intelligence.recommendations.append(
                "Review orphan files."
            )

        return intelligence