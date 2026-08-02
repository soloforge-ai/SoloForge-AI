from pathlib import Path


class CurrentSprintWriter:

    def write(
        self,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Current Sprint")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")
        lines.append("## Sprint")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Completed")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## In Progress")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Next")
        lines.append("")
        lines.append("-")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )