"""
SoloForge AI
MiniBoss Engine V2

Stock Engine
"""

from .constants import MIN_STOCK
from .result import create_score


def score_stock(product, rules):
    """
    Calculate stock score.
    """

    stock = product.get("stock", 0)

    weight = rules["weights"]["stock"]

    score = weight if stock >= MIN_STOCK else 0

    return create_score(
        name="stock",
        score=score,
        value=stock,
        max_value=1,
        weight=weight,
        passed=stock >= MIN_STOCK,
        reason="In Stock" if stock >= MIN_STOCK else None,
    )