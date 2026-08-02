from collections import defaultdict
from pathlib import Path


class ArchitectureWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        groups = defaultdict(int)

        for item in inventory:
            groups[item.category] += 1

        lines = []

        lines.append("# SoloForge AI Architecture")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")

        lines.append("## Project Overview")
        lines.append("")
        lines.append(f"- Total Files : {len(inventory)}")
        lines.append(f"- Total Categories : {len(groups)}")
        lines.append("")

        lines.append("## Modules")
        lines.append("")

        for category in sorted(groups):
            lines.append(
                f"- {category} ({groups[category]} files)"
            )

        lines.append("")
        lines.append("## Layer Overview")
        lines.append("")
        lines.append("- Inventory")
        lines.append("- Builders")
        lines.append("- Writers")
        lines.append("- Output")
        lines.append("- Documentation")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )