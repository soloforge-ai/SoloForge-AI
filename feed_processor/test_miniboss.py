"""
MiniBoss V1 vs V2 Comparison Test
"""

import json
from pathlib import Path

import miniboss
import miniboss_v2

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data" / "processed"


def load_first_product():
    """
    Load the first product from the first ranked_products_*.jsonl file.
    """

    files = sorted(DATA_DIR.glob("ranked_products_*.jsonl"))

    if not files:
        raise FileNotFoundError(
            "No ranked_products_*.jsonl found in data/processed"
        )

    first_file = files[0]

    print(f"Using file: {first_file.name}")

    with open(first_file, "r", encoding="utf-8") as f:
        return json.loads(f.readline())


def main():

    product = load_first_product()

    rules_v1 = miniboss.load_rules()
    rules_v2 = miniboss_v2.load_rules()

    result_v1 = miniboss.analyze(product, rules_v1)
    result_v2 = miniboss_v2.analyze(product, rules_v2)

    print("=" * 60)
    print("MiniBoss V1 vs V2")
    print("=" * 60)

    print()

    print("Score")
    print(result_v1["score"], result_v2["score"])

    print()

    print("Grade")
    print(result_v1["grade"], result_v2["grade"])

    print()

    print("Breakdown Equal")
    print(result_v1["breakdown"] == result_v2["breakdown"])

    print()

    print("Reasons Equal")
    print(result_v1["reasons"] == result_v2["reasons"])

    print()

    print("Full Result Equal")
    print(result_v1 == result_v2)


if __name__ == "__main__":
    main()