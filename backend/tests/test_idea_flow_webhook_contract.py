from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.asset_forge.backend.idea_flow_webhook as webhook


class FakeService:
    claimed_updates: set[int] = set()
    captured: list[tuple[str, str]] = []

    def claim_update(self, update_id: int) -> bool:
        if update_id in self.claimed_updates:
            return False
        self.claimed_updates.add(update_id)
        return True

    def capture(self, body: str, *, actor: str) -> int:
        self.captured.append((body, actor))
        return 42


def _client(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-must-not-appear")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "123456")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "supabase-secret-must-not-appear")
    app = FastAPI()
    app.include_router(webhook.router)
    return TestClient(app)


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
    FakeService.claimed_updates.clear()
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
    FakeService.claimed_updates.clear()
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


def test_research_usage_error_does_not_call_storage():
    class ResearchService:
        def mark_researched(self, *args, **kwargs):
            raise AssertionError("empty research must be rejected before storage")

    assert webhook.handle_text(ResearchService(), "/research 7", actor="test") == "ใช้: /research ID TEXT"
