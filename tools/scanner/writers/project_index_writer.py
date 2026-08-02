from pathlib import Path


class ProjectIndexWriter:

    def write(
        self,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Project Index")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")
        lines.append("## Pages")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Services")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Models")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Widgets")
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