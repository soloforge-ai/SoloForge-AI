from __future__ import annotations

from backend.asset_forge.backend import performance_ingestion


def test_aggregate_latest_snapshots_deduplicates_time_series() -> None:
    rows = [
        {
            "content_job_id": "job-1",
            "platform": "tiktok",
            "views": 120,
            "reactions": 10,
            "comments": 2,
            "shares": 1,
            "saves": 3,
            "clicks": 4,
        },
        {
            "content_job_id": "job-1",
            "platform": "tiktok",
            "views": 100,
            "reactions": 8,
            "comments": 1,
            "shares": 1,
            "saves": 2,
            "clicks": 3,
        },
        {
            "content_job_id": "job-2",
            "platform": "instagram",
            "views": 80,
            "reactions": 5,
            "comments": 1,
            "shares": 0,
            "saves": 2,
            "clicks": 0,
        },
    ]

    result = performance_ingestion.aggregate_latest_snapshots(rows)

    assert result["latest_series"] == 2
    assert result["total_views"] == 200
    assert result["total_interactions"] == 28
    assert result["engagement_rate_percent"] == 14.0


def test_provider_capabilities_marks_current_media_platforms_metadata_only(monkeypatch) -> None:
    monkeypatch.setattr(
        performance_ingestion,
        "list_connections",
        lambda: [
            {
                "platformId": "tiktok-account",
                "username": "creator",
                "connectionStatus": "active",
                "tokenStatus": "valid",
            }
        ],
    )

    result = performance_ingestion.provider_capabilities()

    assert result == [
        {
            "provider": "publora",
            "platform": "tiktok",
            "platform_id": "tiktok-account",
            "username": "creator",
            "connection_status": "active",
            "token_status": "valid",
            "metadata_sync": True,
            "engagement_metrics": False,
        }
    ]


def test_sync_publora_metadata_records_provider_event_without_fake_metrics(monkeypatch) -> None:
    requests = []

    monkeypatch.setattr(
        performance_ingestion,
        "get_post",
        lambda _: {
            "status": "published",
            "posts": [
                {
                    "platform": "youtube",
                    "status": "published",
                    "postedId": "abc",
                    "permalink": "https://example.test/post",
                }
            ],
        },
    )

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        requests.append((method, path, body))
        return None

    monkeypatch.setattr(performance_ingestion, "_supabase_request", fake_request)

    result = performance_ingestion.sync_publora_metadata(
        {"id": "job-1", "publora_post_id": "group-1"}
    )

    assert result["metrics_ingested"] == 0
    assert result["platform_posts"][0]["metrics_supported"] is False
    assert requests[0][1] == "content_job_events"
    assert requests[0][2]["event_type"] == "PROVIDER_SYNC"
