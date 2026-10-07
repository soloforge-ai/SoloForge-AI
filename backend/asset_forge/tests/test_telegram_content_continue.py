from __future__ import annotations

from types import SimpleNamespace

from backend.asset_forge.backend import combined_telegram_webhook as webhook


class _FakeService:
    def __init__(self, job: dict[str, object]) -> None:
        self.job = job

    def get_content_job(self, job_id: str) -> dict[str, object]:
        assert job_id == self.job["id"]
        return dict(self.job)


class _FakeBackgroundTasks:
    def __init__(self) -> None:
        self.calls: list[tuple[object, tuple[object, ...]]] = []

    def add_task(self, fn, *args, **kwargs) -> None:
        assert not kwargs
        self.calls.append((fn, args))


def _video_job(status: str = "AUDIO_READY") -> dict[str, object]:
    return {
        "id": "db63e174-2977-48b2-b5d0-d0f8f4b46a63",
        "idea": "ลองให้ AI หาเว็บฟรีที่ช่วยสรุปประชุม",
        "status": status,
        "score": 82,
        "publish_platform": "tiktok",
        "publish_status": "PENDING",
        "content_package": {"pipeline_route": "VIDEO"},
    }


def test_content_job_keyboard_only_shows_for_resumable_statuses() -> None:
    assert webhook.content_job_keyboard(_video_job("AUDIO_READY")) is not None
    assert webhook.content_job_keyboard(_video_job("ASSET_READY")) is not None
    assert webhook.content_job_keyboard(_video_job("READY_TO_PUBLISH")) is None
    assert webhook.content_job_keyboard(_video_job("PUBLISHING")) is None


def test_continue_callback_schedules_only_the_selected_job(monkeypatch) -> None:
    job = _video_job("AUDIO_READY")
    tasks = _FakeBackgroundTasks()

    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", lambda: _FakeService(job))

    reply, keyboard, toast = webhook._content_callback(
        f"content:continue:{job['id']}",
        background_tasks=tasks,
    )

    assert keyboard is None
    assert toast == "เริ่มรันต่อแล้ว"
    assert "รับคำสั่งรันต่อแล้ว" in reply
    assert len(tasks.calls) == 1
    fn, args = tasks.calls[0]
    assert fn is webhook._resume_job
    assert args == (job["id"], "AUDIO_READY")


def test_continue_callback_refuses_non_resumable_status(monkeypatch) -> None:
    job = _video_job("READY_TO_PUBLISH")
    tasks = _FakeBackgroundTasks()
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", lambda: _FakeService(job))

    try:
        webhook._content_callback(
            f"content:continue:{job['id']}",
            background_tasks=tasks,
        )
    except ValueError as exc:
        assert "รันต่อไม่ได้" in str(exc)
    else:
        raise AssertionError("Expected non-resumable job to be rejected")

    assert tasks.calls == []
