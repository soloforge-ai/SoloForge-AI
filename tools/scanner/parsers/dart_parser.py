import re
from pathlib import Path

from ..models.inventory_item import InventoryItem


class DartParser:

    CLASS_PATTERN = re.compile(
        r"class\s+([A-Za-z0-9_]+)"
    )

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