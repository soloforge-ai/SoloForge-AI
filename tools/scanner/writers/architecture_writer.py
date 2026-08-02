from pathlib import Path


class ArchitectureWriter:

    def write(
        self,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Architecture")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")
        lines.append("## Frontend")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Scanner")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## AI")
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