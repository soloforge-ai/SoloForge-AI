from pathlib import Path


class ProjectMapWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        lines = []

        lines.append("# SoloForge AI Project Map")
        lines.append("")
        lines.append("> Generated automatically from project dependencies.")
        lines.append("")

        # เรียงตามชื่อไฟล์
        for item in sorted(inventory, key=lambda x: x.name.lower()):

            if not item.dependencies:
                continue

            relative = item.path.replace("\\", "/")
            relative = relative.split("SoloForge-AI/")[-1]

            lines.append(f"## {relative}")
            lines.append("")

            for dependency in item.dependencies:

                dep = dependency.replace("\\", "/")
                dep = dep.split("SoloForge-AI/")[-1]

                lines.append(f"- {dep}")

            lines.append("")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )