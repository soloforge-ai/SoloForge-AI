from __future__ import annotations

from backend.asset_forge.backend import analytics_api


def test_summary_uses_pipeline_timestamps_and_counts(monkeypatch) -> None:
    calls = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append(path)
        if path.startswith("content_jobs?"):
            return [
                {
                    "id": "1",
                    "status": "PUBLISHED",
                    "score": 80,
                    "publish_platform": "tiktok",
                    "publish_status": "PUBLISHED",
                    "created_at": "2026-09-29T00:00:00+00:00",
                    "generated_at": "2026-09-29T00:02:00+00:00",
                    "approved_at": "2026-09-29T00:03:00+00:00",
                    "published_at": "2026-09-29T00:10:00+00:00",
                },
                {
                    "id": "2",
                    "status": "READY_FOR_REVIEW",
                    "score": 70,
                    "publish_platform": "instagram",
                    "publish_status": "PENDING",
                    "created_at": "2026-09-29T01:00:00+00:00",
                    "generated_at": "2026-09-29T01:01:00+00:00",
                    "approved_at": None,
                    "published_at": None,
                },
            ]
        if path.startswith("content_performance_snapshots?"):
            return []
        raise AssertionError(path)

    monkeypatch.setattr(analytics_api, "_supabase_request", fake_request)
    monkeypatch.setattr(analytics_api, "_require_session", lambda _: None)

    result = analytics_api.analytics_summary(None)

    assert result["jobs_total"] == 2
    assert result["published"] == 1
    assert result["review"] == 1
    assert result["failed"] == 0
    assert result["average_score"] == 75.0
    assert result["average_generation_seconds"] == 90.0
    assert result["average_time_to_publish_seconds"] == 600.0
    assert result["performance_available"] is False


def test_timeline_is_scoped_to_requested_job(monkeypatch) -> None:
    paths = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        paths.append(path)
        if path.startswith("content_jobs?id=eq."):
            return [{"id": "job-1", "publora_post_id": None, "publish_platform": "tiktok"}]
        if path.startswith("content_job_events?"):
            return [{"id": 1, "event_type": "BASELINE", "to_status": "NEW"}]
        raise AssertionError(path)

    monkeypatch.setattr(analytics_api, "_supabase_request", fake_request)
    monkeypatch.setattr(analytics_api, "_require_session", lambda _: None)

    result = analytics_api.job_timeline("job-1", None)
    assert result["items"][0]["event_type"] == "BASELINE"
    assert any("content_job_id=eq.job-1" in path for path in paths)



def test_job_feedback_uses_latest_snapshot(monkeypatch) -> None:
    paths = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        paths.append(path)
        if path.startswith("content_jobs?id=eq."):
            return [{
                "id": "job-1",
                "publora_post_id": "group-1",
                "publish_platform": "tiktok",
                "content_package": {"format": "short_video_demo"},
            }]
        if path.startswith("content_performance_snapshots?"):
            return [{
                "content_job_id": "job-1",
                "platform": "tiktok",
                "views": 123,
                "reactions": 10,
                "comments": 1,
                "shares": 1,
                "saves": 1,
                "clicks": 1,
                "observed_at": "2026-09-29T00:00:00+00:00",
            }]
        raise AssertionError(path)

    monkeypatch.setattr(analytics_api, "_supabase_request", fake_request)
    monkeypatch.setattr(analytics_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        analytics_api,
        "evaluate_job_performance",
        lambda job, snapshot: {
            "state": "READY",
            "automation_action": "KEEP_BASELINE",
            "score_adjustment": 0,
            "sample_size": 5,
            "minimum_sample_size": 5,
        },
    )

    result = analytics_api.job_feedback("job-1", None)

    assert result["state"] == "READY"
    assert any("order=observed_at.desc&limit=1" in path for path in paths)
