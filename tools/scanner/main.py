from pathlib import Path

from .inventory import InventoryBuilder
from .scanner import ProjectScanner
from .writers.json_writer import JsonWriter

from .writers.stats_writer import StatsWriter
from .writers.status_writer import StatusWriter
from .writers.markdown_writer import MarkdownWriter
from .writers.project_map_writer import ProjectMapWriter

from .builders.dependency_builder import DependencyBuilder
from .builders.project_intelligence_builder import ProjectIntelligenceBuilder
from .writers.project_intelligence_writer import ProjectIntelligenceWriter
from .builders.reverse_dependency_builder import ReverseDependencyBuilder

def main():

    print("=" * 60)
    print("SoloForge AI Project Scanner")
    print("=" * 60)

    scanner = ProjectScanner()

    files = scanner.scan()

    print(f"Scanning... {len(files)} files")

    inventory = InventoryBuilder().build(
        files,
        )
    inventory = DependencyBuilder().build(
        inventory,
        )

    inventory = ReverseDependencyBuilder().build(
        inventory,
    )
  
    intelligence = ProjectIntelligenceBuilder().build(
        inventory,
        )

    output = (
        Path(__file__).parent
        / "output"
        / "project_inventory.json"
    )

    JsonWriter().write(
        inventory,
        output,
    )

    stats_output = (
        Path(__file__).parent
        / "output"
        / "PROJECT_STATS.md"
    )

    StatsWriter().write(
    inventory,
    stats_output,
    )

    status_output = (
        Path(__file__).parent
        / "output"
        / "PROJECT_STATUS.md"
    )

    StatusWriter().write(
        inventory,
        status_output,
    )

    tree_output = (
    Path(__file__).parent
        / "output"
        / "PROJECT_TREE.md"
    )

    MarkdownWriter().write(
        inventory,
        tree_output,
    )

    map_output = (
        Path(__file__).parent
        / "output"
        / "PROJECT_MAP.md"
    )

    ProjectMapWriter().write(
        inventory,
        map_output,
    )

    intelligence_output = (
        Path(__file__).parent
        / "output"
        / "PROJECT_INTELLIGENCE.md"
    )

    ProjectIntelligenceWriter().write(
        intelligence,
        intelligence_output,
    )

    print(f"Inventory Built : {len(inventory)}")

    print(f"JSON Generated : {output}")

    print("Done.")

if __name__ == "__main__":
    main()