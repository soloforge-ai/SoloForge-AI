"""SoloForge application sessions, independent from AI provider credentials."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)

router = APIRouter(prefix="/auth/soloforge", tags=["soloforge-auth"])

_DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 30
_MAX_TTL_SECONDS = 60 * 60 * 24 * 90


@dataclass(frozen=True)
class SoloForgeSession:
    session_id: str
    expires_at: int


class SessionExchangeRequest(BaseModel):
    """Exchange a currently valid legacy provider session for an app session."""

    legacy_authorization: str | None = Field(default=None, exclude=True)


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


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session() -> SoloForgeSession:
    expires_at = int(time.time()) + _ttl_seconds()
    nonce = secrets.token_urlsafe(24)
    payload = f"v1.{expires_at}.{nonce}"
    token = f"{payload}.{_sign(payload)}"
    return SoloForgeSession(session_id=token, expires_at=expires_at)


def validate_session_token(token: str | None) -> bool:
    if not token:
        return False
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return False
    payload = ".".join(parts[:3])
    try:
        expires_at = int(parts[1])
    except ValueError:
        return False
    if expires_at <= int(time.time()):
        return False
    try:
        expected = _sign(payload)
    except RuntimeError:
        return False
    return hmac.compare_digest(parts[3], expected)


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


@router.post("/exchange")
def exchange_legacy_session(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Migration bridge: prove an existing Pollinations session once, then detach."""

    if not get_pollinations_access_token_from_authorization(authorization):
        raise HTTPException(
            status_code=401,
            detail="A valid legacy session is required for one-time migration.",
        )
    session = issue_session()
    return {
        "session_token": session.session_id,
        "expires_at": session.expires_at,
        "session_type": "soloforge",
    }


@router.get("/status")
def soloforge_session_status(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    token = bearer_token(authorization)
    return {
        "authenticated": validate_session_token(token),
        "session_type": "soloforge",
    }
