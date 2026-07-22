import json
from datetime import datetime
from pathlib import Path

from ..models.inventory_item import InventoryItem


class JsonWriter:
    def write(
        self,
        inventory: list[InventoryItem],
        output_file: Path,
    ) -> None:

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_files": len(inventory),
            "items": [
                item.to_dict()
                for item in inventory
            ],
        }

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )