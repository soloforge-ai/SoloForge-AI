"""
SoloForge AI
MiniBoss Engine V2

Shop Rating Engine
"""

from .constants import MIN_SHOP_RATING
from .result import create_score


def score_shop_rating(product, rules):
    """
    Calculate shop rating score.
    """

    rating = product.get("shop", {}).get("rating") or 0

    max_rating = rules["limits"]["shop_rating"]
    weight = rules["weights"]["shop_rating"]

    score = (rating / max_rating) * weight

    return create_score(
        name="shop_rating",
        score=score,
        value=rating,
        max_value=max_rating,
        weight=weight,
        passed=rating >= MIN_SHOP_RATING,
        reason=(
            f"High shop rating ({rating}/{max_rating})"
            if rating >= MIN_SHOP_RATING
            else None
        ),
    )