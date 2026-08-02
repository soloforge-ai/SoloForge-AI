from pathlib import Path


class RoadmapWriter:

    def write(
        self,
        intelligence,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Roadmap")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")

        lines.append("## ✅ Completed")
        lines.append("")

        if intelligence.completed_features:
            for item in intelligence.completed_features:
                lines.append(f"- {item}")
        else:
            lines.append("- None")

        lines.append("")

        lines.append("## 🟡 In Progress")
        lines.append("")

        if intelligence.in_progress_features:
            for item in intelligence.in_progress_features:
                lines.append(f"- {item}")
        else:
            lines.append("- None")

        lines.append("")

        lines.append("## 🔲 Planned")
        lines.append("")

        if intelligence.missing_features:
            for item in intelligence.missing_features:
                lines.append(f"- {item}")
        else:
            lines.append("- None")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )