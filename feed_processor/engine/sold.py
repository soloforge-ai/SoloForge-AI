"""
SoloForge AI
MiniBoss Engine V2

Sold Engine
"""

from .constants import MIN_SOLD
from .result import create_score


def score_sold(product, rules):
    """
    Calculate sold score.
    """

    sold = product.get("sold", 0)

    max_sold = rules["limits"]["sold"]
    weight = rules["weights"]["sold"]

    score = min(sold, max_sold) / max_sold * weight

    return create_score(
        name="sold",
        score=score,
        value=sold,
        max_value=max_sold,
        weight=weight,
        passed=sold >= MIN_SOLD,
        reason=(
            f"Popular product ({sold} sold)"
            if sold >= MIN_SOLD
            else None
        ),
    )