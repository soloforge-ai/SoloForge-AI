"""
SoloForge AI
MiniBoss Engine V2

Report Builder
"""


def build_breakdown(scores):
    """
    Convert score list into breakdown dictionary.
    """

    return {
        item["name"]: item
        for item in scores
    }


def build_reasons(scores):
    """
    Extract all positive reasons.
    """

    return [
        item["reason"]
        for item in scores
        if item.get("reason")
    ]


def calculate_total_score(scores):
    """
    Sum every score.
    """

    return round(
        sum(item["score"] for item in scores),
        2,
    )