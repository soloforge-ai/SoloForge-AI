"""
SoloForge AI
MiniBoss Engine V2

Main Orchestrator
"""

from engine.loader import load_rules
from engine.builder import build_scores
from engine.report import (
    build_breakdown,
    build_reasons,
    calculate_total_score,
)
from engine.grade import calculate_grade


def analyze(product, rules):
    """
    Analyze a product and return MiniBoss result.
    """

    scores = build_scores(product, rules)

    breakdown = build_breakdown(scores)

    total_score = calculate_total_score(scores)

    reasons = build_reasons(scores)

    return {
        "score": total_score,
        "grade": calculate_grade(total_score),
        "breakdown": breakdown,
        "reasons": reasons,
    }


__all__ = [
    "load_rules",
    "analyze",
]