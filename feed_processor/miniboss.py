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


REVENUE_DIMENSIONS = (
    "demand",
    "content_fit",
    "monetization",
    "conversion_potential",
    "effort_efficiency",
)


def _bounded_score(value):
    """Normalize one revenue dimension to a 0-100 float."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(100.0, numeric))


def calculate_revenue_score(opportunity):
    """
    Score a monetizable content opportunity.

    Contract:
    Revenue Score =
      Demand + Content Fit + Monetization
      + Conversion Potential + Effort Efficiency

    Each dimension is normalized to 0-100 and weighted equally.
    Missing dimensions score 0 so incomplete opportunities cannot
    accidentally receive an inflated revenue score.
    """
    source = opportunity or {}
    breakdown = {
        key: _bounded_score(source.get(key, 0))
        for key in REVENUE_DIMENSIONS
    }
    score = round(
        sum(breakdown.values()) / len(REVENUE_DIMENSIONS),
        2,
    )
    return {
        "score": score,
        "breakdown": breakdown,
        "formula": "equal_weight_v1",
    }


def analyze(product, rules):
    """
    Analyze a product and return MiniBoss result.

    Existing product score remains backward compatible. When a
    revenue_opportunity payload is present, MiniBoss also emits a
    revenue_score block for content monetization decisions.
    """

    scores = build_scores(product, rules)

    breakdown = build_breakdown(scores)

    total_score = calculate_total_score(scores)

    reasons = build_reasons(scores)

    result = {
        "score": total_score,
        "grade": calculate_grade(total_score),
        "breakdown": breakdown,
        "reasons": reasons,
    }

    revenue_opportunity = product.get("revenue_opportunity")
    if isinstance(revenue_opportunity, dict):
        result["revenue_score"] = calculate_revenue_score(
            revenue_opportunity
        )

    return result


__all__ = [
    "load_rules",
    "analyze",
    "calculate_revenue_score",
]
