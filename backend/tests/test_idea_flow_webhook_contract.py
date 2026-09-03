from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.asset_forge.backend.idea_flow_webhook as webhook


class FakeService:
    update_states: dict[int, dict[str, object]] = {}
    captured: list[tuple[str, str]] = []

    def __init__(self):
        self.mutation_committed = False

    def claim_update(self, update_id: int) -> dict[str, object]:
        state = self.update_states.get(update_id, {"status": "NEW"})
        status = state["status"]
        if status == "DELIVERED":
            return {"action": "DELIVERED"}
        if status == "SENDING":
            return {"action": "RETRY_REPLY", "response_text": state["reply"]}
        if status == "PROCESSED":
            return {"action": "RESUME_RESULT", "result": state["result"]}
        self.update_states[update_id] = {"status": "PROCESSING"}
        return {"action": "PROCESS"}

    def prepare_reply(self, update_id: int, response_text: str) -> None:
        if self.update_states[update_id]["status"] != "PROCESSING":
            raise RuntimeError("update is no longer processing")
        self.update_states[update_id].update(status="SENDING", reply=response_text)

    def prepare_result_reply(self, update_id: int, response_text: str) -> None:
        if self.update_states[update_id]["status"] != "PROCESSED":
            raise RuntimeError("mutation result is not ready")
        self.update_states[update_id].update(status="SENDING", reply=response_text)

    def mark_delivered(self, update_id: int) -> None:
        self.update_states[update_id]["status"] = "DELIVERED"

    def capture(self, body: str, *, actor: str, update_id: int) -> int:
        self.captured.append((body, actor))
        self.update_states[update_id].update(
            status="PROCESSED",
            result={"kind": "capture", "idea_id": 42, "status": "CAPTURED"},
        )
        self.mutation_committed = True
        return 42


def _client(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-must-not-appear")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "123456")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "supabase-secret-must-not-appear")
    app = FastAPI()
    app.include_router(webhook.router)
    return TestClient(app, raise_server_exceptions=False)


def _update(update_id=1, chat_id=123456, text="ทดลองไอเดีย"):
    return {
        "update_id": update_id,
        "message": {"chat": {"id": chat_id}, "text": text},
    }


def test_webhook_fails_closed_when_secret_configuration_is_missing(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET")
    response = client.post("/telegram/idea-inbox/webhook", json=_update())
    assert response.status_code == 503
    assert response.json() == {"detail": "Idea Inbox is not configured"}


def test_webhook_rejects_invalid_telegram_secret(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/telegram/idea-inbox/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json=_update(),
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_unallowed_chat_cannot_read_or_mutate(monkeypatch):
    client = _client(monkeypatch)

    class MustNotInstantiate:
        def __init__(self):
            raise AssertionError("storage must not be touched for an unauthorized chat")

    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", MustNotInstantiate)
    monkeypatch.setattr(
        webhook,
        "_send_telegram",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not reply")),
    )
    response = client.post(
        "/telegram/idea-inbox/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        json=_update(chat_id=999999, text="/list"),
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_authorized_update_captures_and_replies(monkeypatch):
    FakeService.update_states.clear()
    FakeService.captured.clear()
    sent = []
    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", FakeService)
    monkeypatch.setattr(webhook, "_send_telegram", lambda token, chat_id, text: sent.append((token, chat_id, text)))

    response = client.post(
        "/telegram/idea-inbox/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        json=_update(),
    )

    assert response.status_code == 200
    assert FakeService.captured == [("ทดลองไอเดีย", "telegram:123456")]
    assert sent == [("token-must-not-appear", 123456, "จับไว้แล้ว ✅ Idea #42\nสถานะ: CAPTURED")]


def test_duplicate_update_is_acknowledged_without_duplicate_mutation(monkeypatch):
    FakeService.update_states.clear()
    FakeService.captured.clear()
    sent = []
    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", FakeService)
    monkeypatch.setattr(webhook, "_send_telegram", lambda *args: sent.append(args))
    headers = {"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"}

    first = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=88))
    second = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=88))

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(FakeService.captured) == 1
    assert len(sent) == 1


def test_failed_send_leaves_reply_ready_for_retry(monkeypatch):
    FakeService.update_states.clear()
    FakeService.captured.clear()
    sent = []
    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", FakeService)

    def send_once_then_succeed(*args):
        sent.append(args)
        if len(sent) == 1:
            raise RuntimeError("transient Telegram failure")

    monkeypatch.setattr(webhook, "_send_telegram", send_once_then_succeed)
    headers = {"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"}

    first = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=89))
    second = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=89))

    assert first.status_code == 500
    assert second.status_code == 200
    assert len(FakeService.captured) == 1
    assert len(sent) == 2
    assert FakeService.update_states[89]["status"] == "DELIVERED"


def test_reclaimed_processed_mutation_formats_result_without_mutating_again(monkeypatch):
    FakeService.update_states.clear()
    FakeService.captured.clear()
    FakeService.update_states[91] = {
        "status": "PROCESSED",
        "result": {"kind": "capture", "idea_id": 42, "status": "CAPTURED"},
    }
    sent = []
    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", FakeService)
    monkeypatch.setattr(webhook, "_send_telegram", lambda *args: sent.append(args))

    response = client.post(
        "/telegram/idea-inbox/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        json=_update(update_id=91),
    )

    assert response.status_code == 200
    assert FakeService.captured == []
    assert len(sent) == 1
    assert FakeService.update_states[91]["status"] == "DELIVERED"


def test_lost_mutation_response_preserves_success_for_retry(monkeypatch):
    class LostResponseService(FakeService):
        def capture(self, body: str, *, actor: str, update_id: int) -> int:
            super().capture(body, actor=actor, update_id=update_id)
            raise RuntimeError("response lost after commit")

    FakeService.update_states.clear()
    FakeService.captured.clear()
    sent = []
    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", LostResponseService)
    monkeypatch.setattr(webhook, "_send_telegram", lambda *args: sent.append(args))
    headers = {"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"}

    first = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=92))
    second = client.post("/telegram/idea-inbox/webhook", headers=headers, json=_update(update_id=92))

    assert first.status_code == 500
    assert second.status_code == 200
    assert len(FakeService.captured) == 1
    assert len(sent) == 1
    assert "Idea #42" in sent[0][2]
    assert FakeService.update_states[92]["status"] == "DELIVERED"


def test_busy_update_returns_retryable_error(monkeypatch):
    class BusyService(FakeService):
        def claim_update(self, update_id: int) -> dict[str, object]:
            return {"action": "BUSY"}

    client = _client(monkeypatch)
    monkeypatch.setattr(webhook, "SupabaseIdeaFlowService", BusyService)
    response = client.post(
        "/telegram/idea-inbox/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        json=_update(update_id=90),
    )
    assert response.status_code == 503


def test_research_usage_error_does_not_call_storage():
    class ResearchService:
        def mark_researched(self, *args, **kwargs):
            raise AssertionError("empty research must be rejected before storage")

    assert (
        webhook.handle_text(ResearchService(), "/research 7", actor="test", update_id=7)
        == "ใช้: /research ID TEXT"
    )
