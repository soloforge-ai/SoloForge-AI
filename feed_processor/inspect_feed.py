"""
SoloForge AI
Feed Inspector

Inspect CSV columns and sample data.
"""

import csv

from config import INPUT_FILE, ENCODING


def main():

    print("=" * 80)
    print("Shopee Feed Inspector")
    print("=" * 80)

    with open(
        INPUT_FILE,
        "r",
        encoding=ENCODING,
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        # --------------------------
        # Header
        # --------------------------

        print("\nColumns\n")

        for index, column in enumerate(reader.fieldnames, start=1):
            print(f"{index:3d}. {column}")

        # --------------------------
        # Sample Row
        # --------------------------

        print("\n")
        print("=" * 80)
        print("Sample Row")
        print("=" * 80)

        row = next(reader)

        for key, value in row.items():

            value = str(value)

            if len(value) > 100:
                value = value[:100] + "..."

            print(f"{key:<35} : {value}")

    print("\n")
    print("=" * 80)
    print("Inspection Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()