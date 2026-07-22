from pathlib import Path

from .models.inventory_item import InventoryItem
from .parsers.dart_parser import DartParser


class InventoryBuilder:

    CATEGORY_MAP = {
        "models": "Model",
        "services": "Service",
        "repositories": "Repository",
        "widgets": "Widget",
        "pages": "Page",
        "engine": "Engine",
        "ai": "AI",
        "datasources": "Datasource",
        "docs": "Documentation",
        "rules": "Rule",
        "feed_processor": "FeedProcessor",
        "backend": "Backend",
        "tools": "Tool",
    }

    LANGUAGE_MAP = {
        ".dart": "Dart",
        ".py": "Python",
        ".json": "JSON",
        ".md": "Markdown",
    }

    def build(self, files: list[Path]) -> list[InventoryItem]:

        inventory: list[InventoryItem] = []

        parser = DartParser()

        for file in files:

            item = InventoryItem(
                path=str(file),
                name=file.name,
                extension=file.suffix,
                language=self._language(file),
                category=self._category(file),
            )

            if file.suffix == ".dart":
                parser.parse(file, item)

            inventory.append(item)

        return inventory

    def _language(self, file: Path) -> str:
        return self.LANGUAGE_MAP.get(file.suffix, "Unknown")

    def _category(self, file: Path) -> str:

        parts = [p.lower() for p in file.parts]

        for part in parts:

            if part in self.CATEGORY_MAP:
                return self.CATEGORY_MAP[part]

        return "Other"