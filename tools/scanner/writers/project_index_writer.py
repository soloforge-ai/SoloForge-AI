from collections import defaultdict
from pathlib import Path


class ProjectIndexWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        groups = defaultdict(list)

        for item in inventory:
            groups[item.category].append(item)

        lines = []

        lines.append("# SoloForge AI Project Index")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")

        for category in sorted(groups):

            lines.append(f"## {category}")
            lines.append("")

            for item in sorted(
                groups[category],
                key=lambda x: x.name.lower(),
            ):
                lines.append(f"- {item.name}")

            lines.append("")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )