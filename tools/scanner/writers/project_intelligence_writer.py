from pathlib import Path


class ProjectIntelligenceWriter:

    def write(
        self,
        intelligence,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Project Intelligence")
        lines.append("")

        lines.append("## Completed Features")
        lines.append("")

        for item in intelligence.completed_features:
            lines.append(f"- ✅ {item}")

        lines.append("")

        lines.append("## In Progress")
        lines.append("")

        for item in intelligence.in_progress_features:
            lines.append(f"- 🟡 {item}")

        lines.append("")

        lines.append("## Missing Features")
        lines.append("")

        for item in intelligence.missing_features:
            lines.append(f"- ❌ {item}")

        lines.append("")

        lines.append("## Duplicate Filenames")
        lines.append("")

        for item in intelligence.duplicate_files:
            lines.append(f"- {item}")

        lines.append("")

        lines.append("## Possible Orphan Files")
        lines.append("")

        for item in intelligence.orphan_files:
            lines.append(f"- {item}")

        lines.append("")

        lines.append("## Recommendations")
        lines.append("")

        for item in intelligence.recommendations:
            lines.append(f"- {item}")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )