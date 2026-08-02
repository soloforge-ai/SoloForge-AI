from pathlib import Path

from .inventory import InventoryBuilder
from .scanner import ProjectScanner

from .builders.dependency_builder import DependencyBuilder
from .builders.project_intelligence_builder import (
    ProjectIntelligenceBuilder,
)
from .builders.reverse_dependency_builder import (
    ReverseDependencyBuilder,
)

from .writers.json_writer import JsonWriter
from .writers.status_writer import StatusWriter
from .writers.project_map_writer import ProjectMapWriter
from .writers.project_intelligence_writer import (
    ProjectIntelligenceWriter,
)

from .writers.roadmap_writer import RoadmapWriter
from .writers.current_sprint_writer import (
    CurrentSprintWriter,
)
from .writers.project_index_writer import (
    ProjectIndexWriter,
)
from .writers.architecture_writer import (
    ArchitectureWriter,
)


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

    output_dir = (
        Path(__file__).parent
        / "output"
    )

    docs_dir = (
        Path(__file__).parent.parent.parent
        / "docs"
    )

    JsonWriter().write(
        inventory,
        output_dir / "project_inventory.json",
    )

    StatusWriter().write(
        inventory,
        output_dir / "PROJECT_STATUS.md",
    )

    ProjectMapWriter().write(
        inventory,
        output_dir / "PROJECT_MAP.md",
    )

    ProjectIntelligenceWriter().write(
        intelligence,
        output_dir / "PROJECT_INTELLIGENCE.md",
    )

    RoadmapWriter().write(
        docs_dir / "ROADMAP.md",
    )

    CurrentSprintWriter().write(
        inventory,
        docs_dir / "CURRENT_SPRINT.md",
    )

    ProjectIndexWriter().write(
        inventory,
        docs_dir / "PROJECT_INDEX.md",
    )

    ArchitectureWriter().write(
        docs_dir / "ARCHITECTURE.md",
    )

    print(f"Inventory Built : {len(inventory)}")
    print(f"JSON Generated : {output_dir / 'project_inventory.json'}")
    print("Documentation Generated.")
    print("Done.")


if __name__ == "__main__":
    main()