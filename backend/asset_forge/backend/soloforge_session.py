"""Owner-scoped SoloForge application sessions, independent from provider credentials."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/auth/soloforge", tags=["soloforge-auth"])

# Verified in auth.users and auth.identities on 2026-10-04:
# non-anonymous GitHub identity for repository owner soloforge-ai.
_VERIFIED_OWNER_USER_ID = "72112ead-d399-4a40-aa51-ee17811cb10d"
_DEFAULT_TTL_SECONDS = 15 * 60
_MAX_TTL_SECONDS = 60 * 60


@dataclass(frozen=True)
class SoloForgeSession:
    session_id: str
    expires_at: int


def _owner_user_id() -> str:
    # A server-side override supports account recovery without rebuilding the APK.
    return os.getenv("SOLOFORGE_OWNER_USER_ID", _VERIFIED_OWNER_USER_ID).strip()


def _secret() -> bytes:
    value = os.getenv("SOLOFORGE_SESSION_SECRET", "").strip()
    if len(value) < 32:
        raise RuntimeError("SOLOFORGE_SESSION_SECRET must contain at least 32 characters.")
    return value.encode("utf-8")


def _ttl_seconds() -> int:
    raw = os.getenv("SOLOFORGE_SESSION_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        value = int(raw)
    except ValueError:
        value = _DEFAULT_TTL_SECONDS
    return max(300, min(value, _MAX_TTL_SECONDS))


def _not_before() -> int:
    try:
        return max(0, int(os.getenv("SOLOFORGE_SESSION_NOT_BEFORE", "0")))
    except ValueError:
        return 0


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session(user_id: str) -> SoloForgeSession:
    if not _owner_user_id() or user_id != _owner_user_id():
        raise ValueError("Owner identity required")
    issued_at = int(time.time())
    expires_at = issued_at + _ttl_seconds()
    payload = f"v2.{user_id}.{issued_at}.{expires_at}.{secrets.token_urlsafe(24)}"
    return SoloForgeSession(
        session_id=f"{payload}.{_sign(payload)}", expires_at=expires_at
    )


def validate_session_token(token: str | None) -> bool:
    if not token:
        return False
    parts = token.split(".")
    # v1 tokens had no owner binding and must never survive this rollout.
    if len(parts) != 6 or parts[0] != "v2" or not _owner_user_id():
        return False
    try:
        issued_at, expires_at = int(parts[2]), int(parts[3])
    except ValueError:
        return False
    now = int(time.time())
    if (
        parts[1] != _owner_user_id()
        or issued_at < _not_before()
        or issued_at > now + 60
        or expires_at <= now
        or expires_at <= issued_at
        or expires_at - issued_at > _MAX_TTL_SECONDS
    ):
        return False
    payload = ".".join(parts[:5])
    try:
        expected = _sign(payload)
    except RuntimeError:
        return False
    return hmac.compare_digest(parts[5], expected)


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def require_soloforge_session(authorization: str | None) -> None:
    if not validate_session_token(bearer_token(authorization)):
        raise HTTPException(status_code=401, detail="SoloForge session required")


def _supabase_owner_id(authorization: str | None) -> str | None:
    """Verify a Supabase bearer with Auth; only the GitHub owner may bootstrap."""

    token = bearer_token(authorization)
    base_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not token or not base_url or not publishable_key:
        return None
    request = urllib.request.Request(
        f"{base_url}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": publishable_key,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    metadata = payload.get("app_metadata")
    providers = metadata.get("providers", []) if isinstance(metadata, dict) else []
    if (
        str(payload.get("id") or "") != _owner_user_id()
        or payload.get("is_anonymous") is True
        or not isinstance(providers, list)
        or "github" not in providers
    ):
        return None
    return _owner_user_id()


@router.post("/bootstrap")
def bootstrap_first_party_session(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Exchange the verified GitHub owner's Supabase bearer for an app session."""

    if not bearer_token(authorization):
        raise HTTPException(status_code=401, detail="SoloForge owner sign-in required")
    owner_id = _supabase_owner_id(authorization)
    if not owner_id:
        raise HTTPException(status_code=403, detail="SoloForge owner authorization required")
    session = issue_session(owner_id)
    return {
        "session_token": session.session_id,
        "expires_at": session.expires_at,
        "session_type": "soloforge",
        "identity_provider": "supabase_github",
    }


@router.post("/exchange")
def exchange_legacy_session(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Legacy provider identity cannot prove SoloForge ownership."""

    raise HTTPException(status_code=410, detail="Sign in with GitHub in SoloForge")


@router.post("/refresh")
def refresh_soloforge_session(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    owner_id = _supabase_owner_id(authorization)
    if not owner_id:
        raise HTTPException(status_code=403, detail="SoloForge owner authorization required")
    session = issue_session(owner_id)
    return {
        "session_token": session.session_id,
        "expires_at": session.expires_at,
        "session_type": "soloforge",
    }


@router.get("/status")
def soloforge_session_status(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    return {
        "authenticated": validate_session_token(bearer_token(authorization)),
        "session_type": "soloforge",
    }
