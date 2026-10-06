"""GitHub webhook ingress for SoloForge Ops Bot v0.1."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from backend.ops_events import normalize_github_event
from backend.ops_telegram import enqueue_and_deliver


router = APIRouter(prefix="/ops", tags=["ops"])


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _verify_signature(body: bytes, supplied: str | None, secret: str) -> bool:
    if not supplied or not supplied.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


@router.post("/github/webhook")
async def github_ops_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        secret = _required_env("GITHUB_OPS_WEBHOOK_SECRET")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Ops webhook is not configured") from exc

    body = await request.body()
    if not _verify_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not x_github_event or not x_github_delivery:
        raise HTTPException(status_code=400, detail="Missing GitHub webhook metadata")

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload")

    repository = os.getenv("GITHUB_OPS_REPOSITORY", "soloforge-ai/SoloForge-AI").strip()
    event = normalize_github_event(
        x_github_event,
        x_github_delivery,
        payload,
        repository=repository,
    )
    if event is None:
        return {"ok": True, "ignored": True}

    try:
        result = await asyncio.to_thread(enqueue_and_deliver, event)
    except RuntimeError as exc:
        # Return retryable failure. Idempotent event_key prevents duplicate logical alerts.
        raise HTTPException(status_code=503, detail="Ops notification delivery unavailable") from exc

    return {
        "ok": True,
        "ignored": False,
        "notification_id": result["id"],
        "delivered": result["delivered"],
    }
