from __future__ import annotations

from fastapi import BackgroundTasks

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

    background_tasks = BackgroundTasks()
    result = content_jobs_api.create_from_idea(
        content_jobs_api.IdeaCreateRequest(
            idea="ลองใช้ AI ทำรูปแล้วหน้าไม่เหมือนกัน",
            recommendation_id="short_video_demo",
            action="generate",
        ),
        background_tasks=background_tasks,
        authorization=None,
    )

    assert result["status"] == "SELECTED"
    assert len(background_tasks.tasks) == 1
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

    background_tasks = BackgroundTasks()
    result = content_jobs_api.create_from_idea(
        content_jobs_api.IdeaCreateRequest(
            idea="เล่าประสบการณ์ตอนทำงานเองทุกอย่าง",
            recommendation_id="personal_post",
            action="save",
        ),
        background_tasks=background_tasks,
        authorization=None,
    )

    assert result["status"] == "BACKLOG"
    assert len(background_tasks.tasks) == 0
    assert result["content_package"]["idea_composer"]["human_action"] == "save"



def test_approve_triggers_job_scoped_routing(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    calls = []

    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "READY_FOR_REVIEW",
            "content_package": {"format": "carousel"},
        },
    )

    def fake_patch(job_id, body):
        calls.append((job_id, body))
        return {"id": job_id, **body}

    monkeypatch.setattr(content_jobs_api, "_patch_job", fake_patch)

    background_tasks = BackgroundTasks()
    result = content_jobs_api.approve_content_job(
        "33333333-3333-3333-3333-333333333333",
        background_tasks=background_tasks,
        authorization=None,
    )

    assert result["status"] == "APPROVED"
    assert len(background_tasks.tasks) == 1
    assert calls[0][0] == "33333333-3333-3333-3333-333333333333"



def test_continue_approved_video_job_runs_job_scoped_pipeline(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        content_jobs_api,
        "route_approved_job",
        lambda job_id: {"id": job_id, "status": "ASSET_QUEUED"},
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_asset_job",
        lambda job_id: calls.append(("asset", job_id)) or True,
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_video_asset_job",
        lambda job_id: calls.append(("audio", job_id)) or True,
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_audio_ready_job",
        lambda job_id: calls.append(("render", job_id)) or True,
    )

    content_jobs_api._continue_approved_job("job-1")

    assert calls == [
        ("asset", "job-1"),
        ("audio", "job-1"),
        ("render", "job-1"),
    ]


def test_continue_approved_video_job_stops_when_asset_fails(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        content_jobs_api,
        "route_approved_job",
        lambda job_id: {"id": job_id, "status": "ASSET_QUEUED"},
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_asset_job",
        lambda job_id: calls.append(("asset", job_id)) or False,
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_video_asset_job",
        lambda job_id: calls.append(("audio", job_id)) or True,
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_audio_ready_job",
        lambda job_id: calls.append(("render", job_id)) or True,
    )

    content_jobs_api._continue_approved_job("job-2")

    assert calls == [("asset", "job-2")]


def test_continue_endpoint_resumes_asset_ready_video_job(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "ASSET_READY",
            "content_package": {"pipeline_route": "VIDEO"},
        },
    )

    background_tasks = BackgroundTasks()
    result = content_jobs_api.continue_content_job(
        "resume-job",
        background_tasks=background_tasks,
        authorization=None,
    )

    assert result["status"] == "ASSET_READY"
    assert len(background_tasks.tasks) == 1


def test_resume_asset_ready_runs_audio_then_render(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        content_jobs_api,
        "process_video_asset_job",
        lambda job_id: calls.append(("audio", job_id)) or True,
    )
    monkeypatch.setattr(
        content_jobs_api,
        "process_audio_ready_job",
        lambda job_id: calls.append(("render", job_id)) or True,
    )

    content_jobs_api._resume_job("resume-job", "ASSET_READY")

    assert calls == [
        ("audio", "resume-job"),
        ("render", "resume-job"),
    ]


def test_continue_endpoint_rejects_non_video_job(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "ASSET_READY",
            "content_package": {"pipeline_route": "VISUAL"},
        },
    )

    background_tasks = BackgroundTasks()
    try:
        content_jobs_api.continue_content_job(
            "visual-job",
            background_tasks=background_tasks,
            authorization=None,
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
        assert "video" in str(getattr(exc, "detail", "")).lower()
    else:
        raise AssertionError("non-video resume must be rejected")

    assert len(background_tasks.tasks) == 0


def test_draft_edit_marks_semantic_fidelity_stale(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "READY_FOR_REVIEW",
            "content_package": {
                "format": "carousel",
                "semantic_fidelity": {
                    "status": "PASS",
                    "reason": "Generated body preserves subject anchors.",
                    "required_anchors": ["automation"],
                    "matched_anchors": ["automation"],
                },
            },
        },
    )

    patched = {}

    def fake_patch(job_id, body):
        patched.update(body)
        return {"id": job_id, "status": "READY_FOR_REVIEW", **body}

    monkeypatch.setattr(content_jobs_api, "_patch_job", fake_patch)

    result = content_jobs_api.update_content_draft(
        "44444444-4444-4444-4444-444444444444",
        content_jobs_api.ContentDraftUpdate(caption="Edited caption"),
        authorization=None,
    )

    semantic = result["content_package"]["semantic_fidelity"]
    assert semantic["status"] == "STALE"
    assert "Regenerate before approval" in semantic["reason"]
    assert semantic["stale_at"]


def test_approve_rejects_failed_or_stale_semantic_fidelity(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)

    for semantic_status in ("FAIL", "STALE"):
        monkeypatch.setattr(
            content_jobs_api,
            "_get_row",
            lambda job_id, status=semantic_status: {
                "id": job_id,
                "status": "READY_FOR_REVIEW",
                "content_package": {
                    "format": "carousel",
                    "semantic_fidelity": {"status": status},
                },
            },
        )

        background_tasks = BackgroundTasks()
        try:
            content_jobs_api.approve_content_job(
                "55555555-5555-5555-5555-555555555555",
                background_tasks=background_tasks,
                authorization=None,
            )
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 409
            assert "semantic fidelity" in str(getattr(exc, "detail", "")).lower()
        else:
            raise AssertionError(f"{semantic_status} semantic status must block approval")

        assert len(background_tasks.tasks) == 0



def test_asset_preview_returns_signed_media_url(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "READY_TO_PUBLISH",
            "content_package": {
                "pipeline_route": "VISUAL",
                "asset_status": "READY",
                "asset_storage_path": f"{job_id}/cover.png",
            },
        },
    )
    monkeypatch.setattr(
        content_jobs_api,
        "media_urls_for_job",
        lambda job: ["https://example.invalid/signed-cover.png"],
    )

    result = content_jobs_api.get_asset_preview(
        "66666666-6666-6666-6666-666666666666",
        authorization=None,
    )

    assert result["url"] == "https://example.invalid/signed-cover.png"
    assert result["media_type"] == "image"
    assert result["asset_status"] == "READY"
    assert result["pipeline_route"] == "VISUAL"


def test_asset_preview_returns_404_when_asset_missing(monkeypatch) -> None:
    monkeypatch.setattr(content_jobs_api, "_require_session", lambda _: None)
    monkeypatch.setattr(
        content_jobs_api,
        "_get_row",
        lambda job_id: {
            "id": job_id,
            "status": "READY_TO_PUBLISH",
            "content_package": {
                "pipeline_route": "VISUAL",
                "asset_status": "PENDING",
            },
        },
    )
    monkeypatch.setattr(content_jobs_api, "media_urls_for_job", lambda job: [])

    try:
        content_jobs_api.get_asset_preview(
            "77777777-7777-7777-7777-777777777777",
            authorization=None,
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
        assert "generated asset" in str(getattr(exc, "detail", "")).lower()
    else:
        raise AssertionError("missing asset preview must return 404")
