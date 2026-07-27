"""
SoloForge AI
MiniBoss Engine V2

Preferred Shop Engine
"""

from .result import create_score


def score_preferred(product, rules):
    """
    Calculate preferred shop score.
    """

    preferred = product.get("shop", {}).get("preferred", False)

    weight = rules["weights"]["preferred_shop"]

    score = weight if preferred else 0

    return create_score(
        name="preferred_shop",
        score=score,
        value=preferred,
        max_value=True,
        weight=weight,
        passed=preferred,
        reason="Preferred Shop" if preferred else None,
    )