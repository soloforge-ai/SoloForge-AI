"""FastAPI routes for SoloForge's Pollinations BYOP OAuth flow."""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Header, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from backend.pollinations_oauth import (
    PollinationsOAuthConfig,
    build_authorization_url,
    create_pkce_transaction,
    exchange_authorization_code,
)

router = APIRouter(prefix="/auth/pollinations", tags=["pollinations-auth"])
_TRANSACTION_TTL_SECONDS = 600
_HANDOFF_TTL_SECONDS = 120
_SESSION_COOKIE = "__Host-soloforge_session"
_STATE_COOKIE = "__Host-soloforge_oauth_state"
_DEFAULT_MOBILE_RETURN_TO = "soloforge://oauth/pollinations"


@dataclass
class _OAuthTransaction:
    verifier: str
    created_at: float
    return_to: str | None = None


@dataclass
class _OAuthSession:
    access_token: str
    expires_at: float
    scope: str


@dataclass
class _MobileHandoff:
    session_id: str
    created_at: float


class MobileExchangeRequest(BaseModel):
    """One-time mobile OAuth handoff payload.

    Keep the handoff code in the request body so it is less likely to be
    persisted by reverse-proxy/access logs than a query-string credential.
    """

    code: str = Field(min_length=1, max_length=512)


_lock = threading.RLock()
_transactions: dict[str, _OAuthTransaction] = {}
_sessions: dict[str, _OAuthSession] = {}
_handoffs: dict[str, _MobileHandoff] = {}


def _supabase_config() -> tuple[str, str] | None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        return None
    return url, key


def _supabase_request(
    method: str,
    path: str,
    *,
    body: dict[str, object] | None = None,
    prefer: str | None = None,
) -> bytes | None:
    config = _supabase_config()
    if config is None:
        return None

    base_url, secret_key = config
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer

    request = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        diagnostic: dict[str, object] = {}
        try:
            raw_error = exc.read(4096)
            parsed_error = json.loads(raw_error.decode("utf-8", errors="replace"))
            if isinstance(parsed_error, dict):
                for key in ("code", "message", "hint"):
                    value = parsed_error.get(key)
                    if value is not None:
                        diagnostic[key] = value
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            diagnostic = {"response": "<non-json error omitted>"}
        print(
            "supabase_session_store_http_error",
            {
                "method": method,
                "status": exc.code,
                "reason": str(exc.reason),
                "diagnostic": diagnostic,
            },
        )
        raise RuntimeError("Supabase session store is unavailable.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            "supabase_session_store_transport_error",
            {
                "method": method,
                "exception_type": type(exc).__name__,
            },
        )
        raise RuntimeError("Supabase session store is unavailable.") from exc


def _persist_session(session_id: str, session: _OAuthSession) -> None:
    if _supabase_config() is None:
        return

    expires_at = datetime.fromtimestamp(session.expires_at, tz=timezone.utc).isoformat()
    _supabase_request(
        "POST",
        "pollinations_sessions?on_conflict=session_id",
        body={
            "session_id": session_id,
            "access_token": session.access_token,
            "token_type": "Bearer",
            "scope": session.scope,
            "expires_at": expires_at,
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        },
        prefer="resolution=merge-duplicates,return=minimal",
    )


def _load_persisted_session(session_id: str) -> _OAuthSession | None:
    if _supabase_config() is None:
        return None

    encoded = urllib.parse.quote(session_id, safe="")
    raw = _supabase_request(
        "GET",
        "pollinations_sessions"
        f"?session_id=eq.{encoded}&select=access_token,expires_at,scope&limit=1",
    )
    if not raw:
        return None

    try:
        rows = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Supabase returned an invalid session payload.") from exc

    if not rows:
        return None

    row = rows[0]
    expires_text = str(row.get("expires_at") or "")
    try:
        expires_at = datetime.fromisoformat(expires_text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None

    if expires_at <= time.time():
        _delete_persisted_session(session_id)
        return None

    token = str(row.get("access_token") or "")
    if not token:
        return None

    return _OAuthSession(
        access_token=token,
        expires_at=expires_at,
        scope=str(row.get("scope") or ""),
    )


def _delete_persisted_session(session_id: str) -> None:
    if _supabase_config() is None:
        return
    encoded = urllib.parse.quote(session_id, safe="")
    _supabase_request(
        "DELETE",
        f"pollinations_sessions?session_id=eq.{encoded}",
        prefer="return=minimal",
    )


def _cleanup() -> None:
    now = time.time()
    with _lock:
        for state, transaction in list(_transactions.items()):
            if now - transaction.created_at > _TRANSACTION_TTL_SECONDS:
                _transactions.pop(state, None)
        for session_id, session in list(_sessions.items()):
            if session.expires_at <= now:
                _sessions.pop(session_id, None)
        for code, handoff in list(_handoffs.items()):
            if now - handoff.created_at > _HANDOFF_TTL_SECONDS:
                _handoffs.pop(code, None)


def _cookie_secure() -> bool:
    return os.getenv("POLLINATIONS_SESSION_COOKIE_SECURE", "true").strip().lower() == "true"


def _set_state_cookie(response: RedirectResponse, state: str) -> None:
    response.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
        max_age=_TRANSACTION_TTL_SECONDS,
    )


def _set_session_cookie(response: RedirectResponse, session_id: str) -> None:
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=session_id,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def _clear_state_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(
        key=_STATE_COOKIE,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        key=_SESSION_COOKIE,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def _get_session(session_id: str | None) -> _OAuthSession | None:
    if not session_id:
        return None
    _cleanup()
    with _lock:
        session = _sessions.get(session_id)
    if session is not None:
        return session

    try:
        session = _load_persisted_session(session_id)
    except RuntimeError:
        return None
    if session is not None:
        with _lock:
            _sessions[session_id] = session
    return session


def _session_id_from_authorization(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def _validate_return_to(return_to: str | None) -> str | None:
    if not return_to:
        return None
    allowed = os.getenv(
        "POLLINATIONS_MOBILE_RETURN_TO",
        _DEFAULT_MOBILE_RETURN_TO,
    ).strip()
    if return_to != allowed:
        raise HTTPException(status_code=400, detail="Unsupported mobile return URL.")
    return return_to


@router.get("/login")
def pollinations_login(
    client: str | None = Query(default=None),
    return_to: str | None = Query(default=None),
) -> RedirectResponse:
    try:
        config = PollinationsOAuthConfig.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    mobile_return_to = None
    if client == "mobile":
        mobile_return_to = _validate_return_to(return_to or _DEFAULT_MOBILE_RETURN_TO)

    verifier, challenge, state = create_pkce_transaction()
    with _lock:
        _transactions[state] = _OAuthTransaction(
            verifier=verifier,
            created_at=time.time(),
            return_to=mobile_return_to,
        )

    authorization_url = build_authorization_url(
        config,
        code_challenge=challenge,
        state=state,
    )
    response = RedirectResponse(url=authorization_url, status_code=302)
    _set_state_cookie(response, state)
    return response


@router.get("/callback")
def pollinations_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=_STATE_COOKIE),
):
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
        payload = exchange_authorization_code(
            config,
            code=code,
            code_verifier=transaction.verifier,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Pollinations token exchange failed.") from exc

    session_id = secrets.token_urlsafe(32)
    expires_in = int(payload.get("expires_in", 604800))
    session = _OAuthSession(
        access_token=payload["access_token"],
        expires_at=time.time() + max(60, expires_in),
        scope=str(payload.get("scope", "")),
    )
    with _lock:
        _sessions[session_id] = session
    try:
        _persist_session(session_id, session)
    except RuntimeError as exc:
        with _lock:
            _sessions.pop(session_id, None)
        raise HTTPException(
            status_code=503,
            detail="Could not persist Pollinations session. Please try again.",
        ) from exc

    if transaction.return_to:
        handoff_code = secrets.token_urlsafe(32)
        with _lock:
            _handoffs[handoff_code] = _MobileHandoff(
                session_id=session_id,
                created_at=time.time(),
            )
        separator = "&" if "?" in transaction.return_to else "?"
        target = f"{transaction.return_to}{separator}{urlencode({'code': handoff_code})}"
        response = RedirectResponse(url=target, status_code=302)
        _clear_state_cookie(response)
        return response

    response = RedirectResponse(url="/auth/pollinations/status", status_code=302)
    _set_session_cookie(response, session_id)
    _clear_state_cookie(response)
    return response


@router.post("/mobile/exchange")
def pollinations_mobile_exchange(payload: MobileExchangeRequest) -> dict[str, object]:
    _cleanup()
    with _lock:
        handoff = _handoffs.pop(payload.code, None)
    if handoff is None:
        raise HTTPException(status_code=400, detail="Invalid or expired mobile handoff code.")

    session = _get_session(handoff.session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Pollinations session has expired.")

    return {
        "session_token": handoff.session_id,
        "expires_at": int(session.expires_at),
        "scope": session.scope,
    }


@router.get("/status")
def pollinations_status(
    session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    bearer_session_id = _session_id_from_authorization(authorization)
    session = _get_session(bearer_session_id or session_id)
    if session is None:
        return {"connected": False}
    return {
        "connected": True,
        "expires_at": int(session.expires_at),
        "scope": session.scope,
    }


@router.post("/logout")
def pollinations_logout(
    session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    resolved_session_id = _session_id_from_authorization(authorization) or session_id
    if resolved_session_id:
        with _lock:
            _sessions.pop(resolved_session_id, None)
        try:
            _delete_persisted_session(resolved_session_id)
        except RuntimeError:
            pass
    response = JSONResponse({"connected": False})
    _clear_session_cookie(response)
    return response


def get_pollinations_access_token(session_id: str | None) -> str | None:
    session = _get_session(session_id)
    return session.access_token if session else None


def get_pollinations_access_token_from_authorization(
    authorization: str | None,
) -> str | None:
    session_id = _session_id_from_authorization(authorization)
    return get_pollinations_access_token(session_id)
