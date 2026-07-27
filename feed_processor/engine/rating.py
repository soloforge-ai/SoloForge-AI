"""
SoloForge AI
MiniBoss Engine V2

Product Rating Engine
"""

from .constants import MIN_PRODUCT_RATING
from .result import create_score


def score_rating(product, rules):
    """
    Calculate product rating score.
    """

    rating = product.get("rating", 0)

    max_rating = rules["limits"]["rating"]
    weight = rules["weights"]["rating"]

    score = (rating / max_rating) * weight

    return create_score(
        name="rating",
        score=score,
        value=rating,
        max_value=max_rating,
        weight=weight,
        passed=rating >= MIN_PRODUCT_RATING,
        reason=(
            f"High product rating ({rating}/{max_rating})"
            if rating >= MIN_PRODUCT_RATING
            else None
        ),
    )