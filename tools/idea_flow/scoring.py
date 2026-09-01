from __future__ import annotations

WEIGHTS = {
    "demand": 0.45,
    "feasibility": 0.20,
    "strategic_fit": 0.35,
}


def validate_score(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
        raise ValueError("Scores must be integers from 0 to 5.")


def weighted_score(demand: int, feasibility: int, strategic_fit: int) -> float:
    for value in (demand, feasibility, strategic_fit):
        validate_score(value)
    return round(
        demand * WEIGHTS["demand"]
        + feasibility * WEIGHTS["feasibility"]
        + strategic_fit * WEIGHTS["strategic_fit"],
        2,
    )


def score_signal(score: float) -> str:
    if score >= 4.0:
        return "GRADUATE_CANDIDATE"
    if score >= 3.0:
        return "PARK_OR_REVIEW"
    return "REJECT_CANDIDATE"
