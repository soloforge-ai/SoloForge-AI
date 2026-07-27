"""
SoloForge AI
MiniBoss Engine V2

Official Shop Engine
"""

from .result import create_score


def score_official(product, rules):
    """
    Calculate official shop score.
    """

    official = product.get("shop", {}).get("official", False)

    weight = rules["weights"]["official_shop"]

    score = weight if official else 0

    return create_score(
        name="official_shop",
        score=score,
        value=official,
        max_value=True,
        weight=weight,
        passed=official,
        reason="Official Shop" if official else None,
    )