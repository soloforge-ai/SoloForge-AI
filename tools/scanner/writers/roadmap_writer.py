from pathlib import Path


class RoadmapWriter:

    def write(
        self,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Roadmap")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")
        lines.append("## Phase 1")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Phase 2")
        lines.append("")
        lines.append("-")
        lines.append("")
        lines.append("## Phase 3")
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