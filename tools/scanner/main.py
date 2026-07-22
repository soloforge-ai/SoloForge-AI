from pathlib import Path

from .inventory import InventoryBuilder
from .scanner import ProjectScanner
from .writers.json_writer import JsonWriter


def main():

    print("=" * 60)
    print("SoloForge AI Project Scanner")
    print("=" * 60)

    scanner = ProjectScanner()

    files = scanner.scan()

    print(f"Scanning... {len(files)} files")

    inventory = InventoryBuilder().build(files)

    output = (
        Path(__file__).parent
        / "output"
        / "project_inventory.json"
    )

    JsonWriter().write(
        inventory,
        output,
    )

    print(f"Inventory Built : {len(inventory)}")

    print(f"JSON Generated : {output}")

    print("Done.")