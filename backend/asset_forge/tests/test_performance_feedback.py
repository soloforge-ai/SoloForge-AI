from __future__ import annotations

from backend.asset_forge.backend import performance_feedback


def test_feedback_requires_minimum_sample(monkeypatch) -> None:
    monkeypatch.setattr(
        performance_feedback,
        "_load_evidence",
        lambda: [
            {
                "content_job_id": "job-1",
                "platform": "tiktok",
                "views": 100,
                "reactions": 10,
                "comments": 0,
                "shares": 0,
                "saves": 0,
                "clicks": 0,
            }
        ],
    )
    monkeypatch.setattr(
        performance_feedback,
        "_load_jobs",
        lambda _: {
            "job-1": {
                "id": "job-1",
                "publish_platform": "tiktok",
                "content_package": {"format": "short_video_demo"},
                "hook": "Example hook",
                "score": 70,
            }
        },
    )

    result = performance_feedback.build_feedback_context(
        platform="tiktok",
        content_format="short_video_demo",
    )

    assert result["state"] == "INSUFFICIENT_DATA"
    assert result["sample_size"] == 1
    assert result["score_adjustment"] == 0
    assert result["automation_action"] == "COLLECT_MORE_DATA"


def test_feedback_builds_benchmark_and_examples(monkeypatch) -> None:
    evidence = []
    jobs = {}
    for index, views in enumerate([100, 120, 140, 160, 300], start=1):
        job_id = f"job-{index}"
        evidence.append(
            {
                "content_job_id": job_id,
                "platform": "tiktok",
                "views": views,
                "reactions": 10 + index,
                "comments": 1,
                "shares": 1,
                "saves": 1,
                "clicks": 1,
            }
        )
        jobs[job_id] = {
            "id": job_id,
            "publish_platform": "tiktok",
            "content_package": {"format": "short_video_demo"},
            "hook": f"Hook {index}",
            "score": 70 + index,
        }

    monkeypatch.setattr(performance_feedback, "_load_evidence", lambda: evidence)
    monkeypatch.setattr(performance_feedback, "_load_jobs", lambda _: jobs)

    result = performance_feedback.build_feedback_context(
        platform="tiktok",
        content_format="short_video_demo",
    )

    assert result["state"] == "READY"
    assert result["sample_size"] == 5
    assert result["benchmark"]["median_views"] == 140.0
    assert result["top_examples"]
    assert result["score_adjustment"] == 0


def test_job_feedback_is_advisory_and_capped(monkeypatch) -> None:
    monkeypatch.setattr(
        performance_feedback,
        "build_feedback_context",
        lambda **_: {
            "version": "test",
            "state": "READY",
            "sample_size": 10,
            "minimum_sample_size": 5,
            "benchmark": {
                "median_views": 100.0,
                "median_engagement_rate_percent": 5.0,
            },
            "top_examples": [],
            "score_adjustment": 0,
            "automation_action": "USE_PERFORMANCE_CONTEXT",
            "generation_guidance": [],
        },
    )

    result = performance_feedback.evaluate_job_performance(
        {
            "publish_platform": "tiktok",
            "content_package": {"format": "short_video_demo"},
        },
        {
            "platform": "tiktok",
            "views": 200,
            "reactions": 20,
            "comments": 2,
            "shares": 2,
            "saves": 2,
            "clicks": 2,
        },
    )

    assert result["score_adjustment"] == 5
    assert result["automation_action"] == "REUSE_PATTERN"
    assert result["job_metrics"]["views"] == 200
