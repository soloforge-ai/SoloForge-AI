"""Service-only durable one-time OAuth claims. No process-local fallback."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from backend import pollinations_oauth_router as oauth_router


class ClaimStoreUnavailable(RuntimeError):
    pass


def _rpc(name: str, payload: dict[str, Any]) -> Any:
    if oauth_router._supabase_config() is None:
        raise ClaimStoreUnavailable("Shared OAuth claim store is not configured")
    try:
        raw = oauth_router._supabase_request("POST", f"rpc/pollinations_oauth_{name}", body=payload)
        if raw is None:
            raise ClaimStoreUnavailable("Shared OAuth claim store returned no response")
        return json.loads(raw.decode("utf-8"))
    except (RuntimeError, ValueError, UnicodeError) as exc:
        raise ClaimStoreUnavailable("Shared OAuth claim store unavailable or ambiguous") from exc


def issue(kind: str, secret: str, owner: str, data: dict[str, Any], ttl: int) -> None:
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    if _rpc("issue", {"p_kind": kind, "p_claim_hash": digest,
                       "p_owner": owner, "p_payload": data,
                       "p_expires_at": expiry}) is not True:
        raise ClaimStoreUnavailable("OAuth claim issue not confirmed")


def consume(kind: str, secret: str, owner: str) -> dict[str, Any] | None:
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    value = _rpc("consume", {"p_kind": kind, "p_claim_hash": digest, "p_owner": owner})
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ClaimStoreUnavailable("Invalid OAuth claim response")
    return value
