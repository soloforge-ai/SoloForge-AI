"""FastAPI routes for SoloForge's Pollinations BYOP OAuth flow."""

from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from backend.pollinations_oauth import PollinationsOAuthConfig, build_authorization_url, create_pkce_transaction, exchange_authorization_code

router = APIRouter(prefix="/auth/pollinations", tags=["pollinations-auth"])
_TRANSACTION_TTL_SECONDS = 600
_SESSION_COOKIE = "__Host-soloforge_session"
_STATE_COOKIE = "__Host-soloforge_oauth_state"

@dataclass
class _OAuthTransaction:
    verifier: str
    created_at: float

@dataclass
class _OAuthSession:
    access_token: str
    expires_at: float
    scope: str

_lock = threading.RLock()
_transactions: dict[str, _OAuthTransaction] = {}
_sessions: dict[str, _OAuthSession] = {}

def _cleanup() -> None:
    now = time.time()
    with _lock:
        for state, transaction in list(_transactions.items()):
            if now - transaction.created_at > _TRANSACTION_TTL_SECONDS:
                _transactions.pop(state, None)
        for session_id, session in list(_sessions.items()):
            if session.expires_at <= now:
                _sessions.pop(session_id, None)

def _cookie_secure() -> bool:
    return os.getenv("POLLINATIONS_SESSION_COOKIE_SECURE", "true").strip().lower() == "true"

def _set_state_cookie(response: RedirectResponse, state: str) -> None:
    response.set_cookie(key=_STATE_COOKIE, value=state, path="/", secure=_cookie_secure(), httponly=True, samesite="lax", max_age=_TRANSACTION_TTL_SECONDS)

def _set_session_cookie(response: RedirectResponse, session_id: str) -> None:
    response.set_cookie(key=_SESSION_COOKIE, value=session_id, path="/", secure=_cookie_secure(), httponly=True, samesite="lax")

def _clear_state_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(key=_STATE_COOKIE, path="/", secure=_cookie_secure(), httponly=True, samesite="lax")

def _clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(key=_SESSION_COOKIE, path="/", secure=_cookie_secure(), httponly=True, samesite="lax")

def _get_session(session_id: str | None) -> _OAuthSession | None:
    if not session_id:
        return None
    _cleanup()
    with _lock:
        return _sessions.get(session_id)

@router.get("/login")
def pollinations_login() -> RedirectResponse:
    try:
        config = PollinationsOAuthConfig.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    verifier, challenge, state = create_pkce_transaction()
    with _lock:
        _transactions[state] = _OAuthTransaction(verifier=verifier, created_at=time.time())
    authorization_url = build_authorization_url(config, code_challenge=challenge, state=state)
    response = RedirectResponse(url=authorization_url, status_code=302)
    _set_state_cookie(response, state)
    return response

@router.get("/callback")
def pollinations_callback(code: str | None = None, state: str | None = None, error: str | None = None, oauth_state: str | None = Cookie(default=None, alias=_STATE_COOKIE)):
    _cleanup()
    if error:
        raise HTTPException(status_code=400, detail="Pollinations authorization was denied or failed.")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback parameters.")
    if not oauth_state or not secrets.compare_digest(state, oauth_state):
        raise HTTPException(status_code=400, detail="OAuth state does not match this browser session.")
    with _lock:
        transaction = _transactions.pop(state, None)
    if transaction is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    try:
        config = PollinationsOAuthConfig.from_env()
        payload = exchange_authorization_code(config, code=code, code_verifier=transaction.verifier)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Pollinations token exchange failed.") from exc
    session_id = secrets.token_urlsafe(32)
    expires_in = int(payload.get("expires_in", 604800))
    with _lock:
        _sessions[session_id] = _OAuthSession(
            access_token=payload["access_token"],
            expires_at=time.time() + max(60, expires_in),
            scope=str(payload.get("scope", "")),
        )
    response = RedirectResponse(url="/auth/pollinations/status", status_code=302)
    _set_session_cookie(response, session_id)
    _clear_state_cookie(response)
    return response

@router.get("/status")
def pollinations_status(session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE)) -> dict[str, object]:
    session = _get_session(session_id)
    if session is None:
        return {"connected": False}
    return {"connected": True, "expires_at": int(session.expires_at), "scope": session.scope}

@router.post("/logout")
def pollinations_logout(session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE)) -> JSONResponse:
    if session_id:
        with _lock:
            _sessions.pop(session_id, None)
    response = JSONResponse({"connected": False})
    _clear_session_cookie(response)
    return response

def get_pollinations_access_token(session_id: str | None) -> str | None:
    session = _get_session(session_id)
    return session.access_token if session else None
