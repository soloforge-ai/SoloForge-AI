"""
SoloForge AI
MiniBoss Engine V2

Shared score result builder.
"""


def create_score(
    name,
    score,
    value,
    max_value,
    weight,
    passed,
    reason=None,
):
    """
    Standard output format for every scoring engine.
    """

    return {
        "name": name,
        "score": round(score, 2),
        "value": value,
        "max": max_value,
        "weight": weight,
        "passed": passed,
        "reason": reason,
    }