import re
from pathlib import Path

from ..models.inventory_item import InventoryItem


class DartParser:

    CLASS_PATTERN = re.compile(
        r"class\s+([A-Za-z0-9_]+)"
    )

    IMPORT_PATTERN = re.compile(
        r"^\s*import\s+['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    METHOD_PATTERN = re.compile(
        r"^\s*(?:static\s+)?(?:[\w<>,?\s]+\s+)?([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:async\s*)?(?:\{|=>)",
        re.MULTILINE,
    )

    EXCLUDED_METHODS = {
        "if",
        "for",
        "while",
        "switch",
        "return",
        "catch",
        "try",
        "else",
        "Scaffold",
        "SizedBox",
        "Card",
        "ChoiceChip",
        "DropdownMenuItem",
        "MaterialPageRoute",
        "ProductCard",
        "_ContentCard",
    }

    def parse(
        self,
        file: Path,
        item: InventoryItem,
    ) -> None:

        text = file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        item.classes.extend(
            self.CLASS_PATTERN.findall(text)
        )

        item.imports.extend(
            self.IMPORT_PATTERN.findall(text)
        )

        methods = [
            method
            for method in self.METHOD_PATTERN.findall(text)
            if method not in self.EXCLUDED_METHODS
        ]

        item.methods.extend(methods)