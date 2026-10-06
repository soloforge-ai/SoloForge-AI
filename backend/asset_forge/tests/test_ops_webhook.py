import hashlib
import hmac
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import ops_webhook


def _signed(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(ops_webhook.router)
    return TestClient(app)


def test_bad_signature_is_rejected(monkeypatch):
    monkeypatch.setenv("GITHUB_OPS_WEBHOOK_SECRET", "secret")
    response = _app().post(
        "/ops/github/webhook",
        content=b"{}",
        headers={
            "X-Hub-Signature-256": "sha256=bad",
            "X-GitHub-Event": "workflow_job",
            "X-GitHub-Delivery": "delivery",
        },
    )
    assert response.status_code == 403


def test_irrelevant_event_is_ignored(monkeypatch):
    monkeypatch.setenv("GITHUB_OPS_WEBHOOK_SECRET", "secret")
    body = json.dumps(
        {"action": "opened", "repository": {"full_name": "soloforge-ai/SoloForge-AI"}}
    ).encode()
    response = _app().post(
        "/ops/github/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _signed(body, "secret"),
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "ignored": True}


def test_runner_unavailable_delivery(monkeypatch):
    monkeypatch.setenv("GITHUB_OPS_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr(
        ops_webhook,
        "enqueue_and_deliver",
        lambda event: {"id": 9, "delivered": True},
    )
    body = json.dumps(
        {
            "action": "completed",
            "repository": {"full_name": "soloforge-ai/SoloForge-AI"},
            "workflow_job": {
                "id": 77,
                "run_id": 88,
                "name": "production-smoke",
                "workflow_name": "Asset Forge Production Smoke",
                "head_sha": "55467d2",
                "conclusion": "cancelled",
                "runner_name": "",
                "steps": [],
            },
        }
    ).encode()
    response = _app().post(
        "/ops/github/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _signed(body, "secret"),
            "X-GitHub-Event": "workflow_job",
            "X-GitHub-Delivery": "delivery",
        },
    )
    assert response.status_code == 200
    assert response.json()["notification_id"] == 9
    assert response.json()["delivered"] is True
