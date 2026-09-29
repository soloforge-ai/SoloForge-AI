from __future__ import annotations

from statistics import median
from typing import Any

from backend.shared_supabase import supabase_request as _supabase_request


FEEDBACK_VERSION = "performance_feedback_v0.1"
MIN_SERIES = 5
MAX_SCORE_ADJUSTMENT = 5


def _engagement_rate(row: dict[str, Any]) -> float | None:
    views = int(row.get("views") or 0)
    if views <= 0:
        return None
    interactions = sum(
        int(row.get(key) or 0)
        for key in ("reactions", "comments", "shares", "saves", "clicks")
    )
    return (interactions / views) * 100.0


def _latest_per_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        key = (
            str(row.get("content_job_id") or ""),
            str(row.get("platform") or "").lower(),
        )
        if key not in latest:
            latest[key] = row
    return list(latest.values())


def _load_evidence() -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_performance_snapshots"
        "?select=content_job_id,platform,views,reactions,comments,shares,saves,clicks,observed_at"
        "&order=observed_at.desc&limit=1000",
    ) or []
    return _latest_per_series([dict(row) for row in rows])


def _load_jobs(job_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not job_ids:
        return {}
    values = ",".join(job_ids)
    rows = _supabase_request(
        "GET",
        "content_jobs"
        f"?id=in.({values})"
        "&select=id,publish_platform,content_package,hook,score",
    ) or []
    return {str(row["id"]): dict(row) for row in rows}


def build_feedback_context(
    *,
    platform: str | None = None,
    content_format: str | None = None,
) -> dict[str, Any]:
    evidence = _load_evidence()
    jobs = _load_jobs(
        [str(row.get("content_job_id") or "") for row in evidence if row.get("content_job_id")]
    )

    candidates: list[dict[str, Any]] = []
    for row in evidence:
        job = jobs.get(str(row.get("content_job_id") or ""))
        if not job:
            continue
        row_platform = str(row.get("platform") or job.get("publish_platform") or "").lower()
        package = dict(job.get("content_package") or {})
        row_format = str(package.get("format") or "content").lower()
        rate = _engagement_rate(row)
        candidates.append(
            {
                **row,
                "platform": row_platform,
                "format": row_format,
                "engagement_rate": rate,
                "hook": job.get("hook"),
                "score": job.get("score"),
            }
        )

    requested_platform = (platform or "").strip().lower()
    requested_format = (content_format or "").strip().lower()

    comparable = [
        row
        for row in candidates
        if (not requested_platform or row["platform"] == requested_platform)
        and (not requested_format or row["format"] == requested_format)
    ]

    if len(comparable) < MIN_SERIES and requested_platform:
        comparable = [
            row for row in candidates if row["platform"] == requested_platform
        ]

    if len(comparable) < MIN_SERIES:
        comparable = candidates

    if len(comparable) < MIN_SERIES:
        return {
            "version": FEEDBACK_VERSION,
            "state": "INSUFFICIENT_DATA",
            "sample_size": len(comparable),
            "minimum_sample_size": MIN_SERIES,
            "score_adjustment": 0,
            "automation_action": "COLLECT_MORE_DATA",
            "generation_guidance": [],
        }

    views = [int(row.get("views") or 0) for row in comparable if int(row.get("views") or 0) > 0]
    rates = [
        float(row["engagement_rate"])
        for row in comparable
        if row.get("engagement_rate") is not None
    ]

    median_views = float(median(views)) if views else 0.0
    median_engagement = float(median(rates)) if rates else None

    ranked = sorted(
        comparable,
        key=lambda row: (
            float(row.get("engagement_rate") or 0.0),
            int(row.get("views") or 0),
        ),
        reverse=True,
    )
    examples = []
    for row in ranked[:3]:
        hook = str(row.get("hook") or "").strip()
        if not hook:
            continue
        examples.append(
            {
                "platform": row["platform"],
                "format": row["format"],
                "hook": hook[:500],
                "views": int(row.get("views") or 0),
                "engagement_rate_percent": (
                    round(float(row["engagement_rate"]), 2)
                    if row.get("engagement_rate") is not None
                    else None
                ),
            }
        )

    guidance = []
    if examples:
        guidance.append(
            "Use the high-performing examples only as evidence of patterns; do not copy wording."
        )
        guidance.append(
            "Prefer hook structures and content angles supported by the comparable performance sample."
        )

    return {
        "version": FEEDBACK_VERSION,
        "state": "READY",
        "sample_size": len(comparable),
        "minimum_sample_size": MIN_SERIES,
        "benchmark": {
            "median_views": round(median_views, 1),
            "median_engagement_rate_percent": (
                round(median_engagement, 2)
                if median_engagement is not None
                else None
            ),
        },
        "top_examples": examples,
        "score_adjustment": 0,
        "automation_action": "USE_PERFORMANCE_CONTEXT",
        "generation_guidance": guidance,
    }


def evaluate_job_performance(
    job: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    package = dict(job.get("content_package") or {})
    context = build_feedback_context(
        platform=str(snapshot.get("platform") or job.get("publish_platform") or ""),
        content_format=str(package.get("format") or ""),
    )
    if context.get("state") != "READY":
        return context

    benchmark = dict(context.get("benchmark") or {})
    median_views = float(benchmark.get("median_views") or 0)
    median_engagement = benchmark.get("median_engagement_rate_percent")
    views = int(snapshot.get("views") or 0)
    engagement = _engagement_rate(snapshot)

    action = "KEEP_BASELINE"
    adjustment = 0
    reasons: list[str] = []

    if median_views > 0:
        if views >= median_views * 1.5:
            adjustment += 2
            reasons.append("views >= 150% of comparable median")
        elif views <= median_views * 0.6:
            adjustment -= 2
            reasons.append("views <= 60% of comparable median")

    if median_engagement is not None and engagement is not None:
        median_engagement = float(median_engagement)
        if engagement >= median_engagement * 1.5:
            adjustment += 3
            reasons.append("engagement >= 150% of comparable median")
        elif engagement <= median_engagement * 0.6:
            adjustment -= 3
            reasons.append("engagement <= 60% of comparable median")

    adjustment = max(-MAX_SCORE_ADJUSTMENT, min(MAX_SCORE_ADJUSTMENT, adjustment))
    if adjustment >= 3:
        action = "REUSE_PATTERN"
    elif adjustment <= -3:
        action = "REVIEW_HOOK_AND_ANGLE"

    return {
        **context,
        "score_adjustment": adjustment,
        "automation_action": action,
        "job_metrics": {
            "views": views,
            "engagement_rate_percent": (
                round(engagement, 2) if engagement is not None else None
            ),
        },
        "reasons": reasons,
    }


def feedback_for_candidate(
    *,
    platform: str | None,
    content_format: str | None,
) -> dict[str, Any]:
    return build_feedback_context(
        platform=platform,
        content_format=content_format,
    )
