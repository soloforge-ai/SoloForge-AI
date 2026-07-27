"""
SoloForge AI
MiniBoss Engine V2

Discount Engine
"""

from .constants import MIN_DISCOUNT
from .result import create_score


def score_discount(product, rules):
    """
    Calculate discount score.
    """

    discount = product.get("discount", 0)

    max_discount = rules["limits"]["discount"]
    weight = rules["weights"]["discount"]

    score = min(discount, max_discount) / max_discount * weight

    return create_score(
        name="discount",
        score=score,
        value=discount,
        max_value=max_discount,
        weight=weight,
        passed=discount >= MIN_DISCOUNT,
        reason=(
            f"{discount:.1f}% discount"
            if discount >= MIN_DISCOUNT
            else None
        ),
    )