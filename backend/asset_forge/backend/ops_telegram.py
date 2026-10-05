"""Durable Telegram delivery for SoloForge operational events."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.ops_events import OpsEvent, format_telegram_message
from backend.shared_supabase import supabase_request


MAX_ATTEMPTS = 3


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _rpc(name: str, body: dict[str, object]) -> Any:
    return supabase_request("POST", f"rpc/{name}", body=body)


def _send_telegram(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ops Telegram delivery failed") from exc
    if not payload.get("ok"):
        raise RuntimeError("Ops Telegram delivery failed")


def enqueue_event(event: OpsEvent) -> dict[str, object]:
    result = _rpc(
        "ops_enqueue_notification",
        {
            "p_event_key": event.event_key,
            "p_category": event.category,
            "p_event_type": event.event_type,
            "p_severity": event.severity,
            "p_source": event.source,
            "p_subject": event.subject,
            "p_commit_sha": event.commit_sha,
            "p_status_label": event.status,
            "p_details": event.details,
        },
    )
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        raise RuntimeError("Ops notification storage returned an invalid enqueue result")
    return result


def _claim(notification_id: int) -> dict[str, object] | None:
    result = _rpc("ops_claim_notification", {"p_notification_id": notification_id})
    if result is None:
        return None
    if not isinstance(result, dict):
        raise RuntimeError("Ops notification storage returned an invalid claim")
    return result


def _mark_sent(notification_id: int) -> None:
    _rpc("ops_mark_notification_sent", {"p_notification_id": notification_id})


def _mark_failed(notification_id: int, error: Exception) -> None:
    _rpc(
        "ops_mark_notification_failed",
        {
            "p_notification_id": notification_id,
            "p_error": type(error).__name__,
            "p_max_attempts": MAX_ATTEMPTS,
        },
    )


def deliver_notification(event: OpsEvent, notification_id: int) -> bool:
    claimed = _claim(notification_id)
    if claimed is None:
        return False

    token = _required_env("TELEGRAM_BOT_TOKEN")
    chat_id = _required_env("TELEGRAM_ALLOWED_CHAT_ID")
    message = format_telegram_message(event, notification_id)
    try:
        _send_telegram(token, chat_id, message)
    except Exception as exc:
        _mark_failed(notification_id, exc)
        raise

    _mark_sent(notification_id)
    return True


def enqueue_and_deliver(event: OpsEvent) -> dict[str, object]:
    row = enqueue_event(event)
    notification_id = int(row["id"])
    delivery_status = str(row.get("delivery_status") or "")
    delivered = False
    if delivery_status == "PENDING":
        delivered = deliver_notification(event, notification_id)
    return {
        "id": notification_id,
        "delivery_status": delivery_status,
        "delivered": delivered,
    }
