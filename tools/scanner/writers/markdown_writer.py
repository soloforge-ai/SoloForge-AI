from collections import defaultdict
from pathlib import Path


class MarkdownWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        folders = defaultdict(list)

        for item in inventory:

            folder = str(Path(item.path).parent)
            folders[folder].append(item.name)

        lines = []

        lines.append("# SoloForge AI Project Tree")
        lines.append("")

        for folder in sorted(folders.keys()):

            lines.append(f"## {folder}")
            lines.append("")

            for file_name in sorted(set(folders[folder])):
                lines.append(f"- {file_name}")

            lines.append("")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )