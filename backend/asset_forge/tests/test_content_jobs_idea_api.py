from __future__ import annotations

from backend.asset_forge.backend import content_jobs_api


def test_analyze_idea_returns_ranked_options() -> None:
    result = content_jobs_api.analyze_idea(
        content_jobs_api.IdeaAnalyzeRequest(
            idea="ลองใช้ AI ทำรูปแล้วหน้าไม่เหมือนกัน"
        )
    )

    assert result["recommended_format"]
    assert len(result["options"]) == 4
    assert result["options"][0]["recommended"] is True


def test_create_from_idea_generates_selected_job(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append((method, path, body, prefer))
        if method == "POST" and path == "content_jobs":
            return [{
                "id": "11111111-1111-1111-1111-111111111111",
                "idea": body["idea"],
                "status": body["status"],
                "score": body["score"],
                "score_reason": body["score_reason"],
                "publish_platform": body["publish_platform"],
                "publish_status": "PENDING",
                "risk_level": "LOW",
                "content_package": body["content_package"],
                "created_at": "2026-09-30T00:00:00+00:00",
                "updated_at": "2026-09-30T00:00:00+00:00",
            }]
        if method == "POST" and path == "content_job_events":
            return None
        raise AssertionError((method, path))

    monkeypatch.setattr(content_jobs_api, "_supabase_request", fake_request)

    result = content_jobs_api.create_from_idea(
        content_jobs_api.IdeaCreateRequest(
            idea="ลองใช้ AI ทำรูปแล้วหน้าไม่เหมือนกัน",
            recommendation_id="short_video_demo",
            action="generate",
        ),
        authorization=None,
    )

    assert result["status"] == "SELECTED"
    assert result["content_package"]["format"] == "short_video_demo"
    assert result["content_package"]["needs_video"] is True
    assert any(
        method == "POST" and path == "content_job_events"
        for method, path, _, _ in calls
    )


def test_create_from_idea_can_save_to_backlog(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        if method == "POST" and path == "content_jobs":
            return [{
                "id": "22222222-2222-2222-2222-222222222222",
                "idea": body["idea"],
                "status": body["status"],
                "content_package": body["content_package"],
            }]
        if method == "POST" and path == "content_job_events":
            return None
        raise AssertionError((method, path))

    monkeypatch.setattr(content_jobs_api, "_supabase_request", fake_request)

    result = content_jobs_api.create_from_idea(
        content_jobs_api.IdeaCreateRequest(
            idea="เล่าประสบการณ์ตอนทำงานเองทุกอย่าง",
            recommendation_id="personal_post",
            action="save",
        ),
        authorization=None,
    )

    assert result["status"] == "BACKLOG"
    assert result["content_package"]["idea_composer"]["human_action"] == "save"
