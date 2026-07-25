from pathlib import Path


class StatusWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        completed = []
        placeholder = []

        for item in inventory:

            if len(item.methods) > 0 or len(item.classes) > 0:
                completed.append(item.name)
            else:
                placeholder.append(item.name)

        lines = []

        lines.append("# SoloForge AI Project Status\n")

        lines.append("## ✅ Completed\n")

        if completed:
            for name in sorted(completed):
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.append("")
        lines.append("## 💤 Placeholder\n")

        if placeholder:
            for name in sorted(placeholder):
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.append("")
        lines.append("## Next Recommended Tasks\n")

        if placeholder:
            for name in sorted(placeholder)[:10]:
                lines.append(f"- Implement {name}")
        else:
            lines.append("- Great job! No placeholder files found.")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )