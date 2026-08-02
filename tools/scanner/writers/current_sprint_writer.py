from pathlib import Path


class CurrentSprintWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        completed = []
        placeholder = []

        for item in inventory:

            if item.methods or item.classes:
                completed.append(item.name)
            else:
                placeholder.append(item.name)

        lines = []

        lines.append("# SoloForge AI Current Sprint")
        lines.append("")
        lines.append("> Generated automatically.")
        lines.append("")

        lines.append("## Project")
        lines.append("")
        lines.append(f"- Total Files : {len(inventory)}")
        lines.append(f"- Completed Files : {len(completed)}")
        lines.append(f"- Placeholder Files : {len(placeholder)}")
        lines.append("")

        lines.append("## Completed")
        lines.append("")

        if completed:
            for name in sorted(completed):
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.append("")

        lines.append("## Placeholder")
        lines.append("")

        if placeholder:
            for name in sorted(placeholder):
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.append("")

        lines.append("## Next Recommended Tasks")
        lines.append("")

        if placeholder:
            for name in sorted(placeholder)[:10]:
                lines.append(f"- Implement {name}")
        else:
            lines.append("- Great job!")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )