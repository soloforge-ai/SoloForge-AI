from pathlib import Path
from collections import Counter


class StatsWriter:

    def write(
        self,
        inventory,
        output: Path,
    ):

        language_counter = Counter()
        category_counter = Counter()

        class_count = 0
        method_count = 0

        for item in inventory:

            language_counter[item.language] += 1
            category_counter[item.category] += 1

            class_count += len(item.classes)
            method_count += len(item.methods)

        lines = []

        lines.append("# SoloForge AI Project Statistics\n")

        lines.append(f"Total Files : {len(inventory)}")
        lines.append(f"Total Classes : {class_count}")
        lines.append(f"Total Methods : {method_count}")
        lines.append("")

        lines.append("## Languages")

        for language, count in sorted(language_counter.items()):
            lines.append(f"- {language}: {count}")

        lines.append("")
        lines.append("## Categories")

        for category, count in sorted(category_counter.items()):
            lines.append(f"- {category}: {count}")

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )