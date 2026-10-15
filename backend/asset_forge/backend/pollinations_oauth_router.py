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

from backend.pollinations_grant_validation import (
    GrantVerificationError,
    strict_expires_in,
    verify_provider_token,
)
from backend.soloforge_session import require_soloforge_session, _owner_user_id
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
_DEFAULT_WEB_RETURN_TO = "https://soloforge-ai-web.onrender.com/"


@dataclass
class _OAuthTransaction:
    verifier: str
    created_at: float
    return_to: str | None = None
    owner_user_id: str = ""


@dataclass
class _OAuthSession:
    access_token: str
    expires_at: float
    scope: str
    owner_user_id: str
    provider_subject: str


@dataclass
class _MobileHandoff:
    session_id: str
    created_at: float
    owner_user_id: str


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
_login_tickets: dict[str, tuple[str, float]] = {}


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
            "owner_user_id": session.owner_user_id,
            "provider_subject": session.provider_subject,
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
        f"?session_id=eq.{encoded}&select=access_token,expires_at,scope,owner_user_id,provider_subject&limit=1",
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

    owner = row.get("owner_user_id")
    subject = row.get("provider_subject")
    if owner != _owner_user_id() or not isinstance(subject, str) or not subject.strip():
        return None  # Legacy and cross-owner rows fail closed.
    return _OAuthSession(
        access_token=token,
        expires_at=expires_at,
        scope=str(row.get("scope") or ""),
        owner_user_id=owner,
        provider_subject=subject,
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
        for ticket, (_, issued) in list(_login_tickets.items()):
            if now - issued > _TRANSACTION_TTL_SECONDS:
                _login_tickets.pop(ticket, None)
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
    # When durable storage is configured, it is authoritative on EVERY read.
    # Never serve a cached credential after another worker has revoked it.
    if _supabase_config() is not None:
        try:
            session = _load_persisted_session(session_id)
        except RuntimeError:
            return None  # Storage outage must not expose a cached token.
        with _lock:
            if session is None:
                _sessions.pop(session_id, None)
            else:
                _sessions[session_id] = session
        return session

    # Offline/local-only mode has no shared revocation store.
    with _lock:
        return _sessions.get(session_id)


def _session_id_from_authorization(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def _validate_return_to(return_to: str | None, *, client: str) -> str | None:
    if not return_to:
        return None
    if client == "mobile":
        allowed = os.getenv(
            "POLLINATIONS_MOBILE_RETURN_TO",
            _DEFAULT_MOBILE_RETURN_TO,
        ).strip()
        error = "Unsupported mobile return URL."
    elif client == "web":
        allowed = os.getenv(
            "POLLINATIONS_WEB_RETURN_TO",
            _DEFAULT_WEB_RETURN_TO,
        ).strip()
        error = "Unsupported web return URL."
    else:
        raise HTTPException(status_code=400, detail="Unsupported OAuth client.")

    if return_to != allowed:
        raise HTTPException(status_code=400, detail=error)
    return return_to


@router.post("/login-ticket")
def pollinations_login_ticket(
    x_soloforge_authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_soloforge_session(x_soloforge_authorization)
    _cleanup()
    ticket = secrets.token_urlsafe(32)
    from backend.pollinations_oauth_claim_store import issue, ClaimStoreUnavailable
    try:
        issue("login_ticket", ticket, _owner_user_id(), {}, _TRANSACTION_TTL_SECONDS)
    except ClaimStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="OAuth claim store unavailable") from exc
    return {"ticket": ticket}


@router.get("/login")
def pollinations_login(
    client: str | None = Query(default=None),
    return_to: str | None = Query(default=None),
    ticket: str | None = Query(default=None),
) -> RedirectResponse:
    try:
        config = PollinationsOAuthConfig.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    resolved_return_to = None
    if client == "mobile":
        resolved_return_to = _validate_return_to(
            return_to or _DEFAULT_MOBILE_RETURN_TO,
            client="mobile",
        )
    elif client == "web":
        resolved_return_to = _validate_return_to(
            return_to or _DEFAULT_WEB_RETURN_TO,
            client="web",
        )

    _cleanup()
    from backend.pollinations_oauth_claim_store import consume, issue, ClaimStoreUnavailable
    if not ticket:
        raise HTTPException(status_code=401, detail="Owner-bound OAuth login ticket required")
    try:
        claim = consume("login_ticket", ticket, _owner_user_id())
    except ClaimStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="OAuth claim store unavailable") from exc
    if claim is None:
        raise HTTPException(status_code=401, detail="Owner-bound OAuth login ticket required")
    verifier, challenge, state = create_pkce_transaction()
    try:
        issue("pkce_state", state, _owner_user_id(),
              {"verifier": verifier, "return_to": resolved_return_to}, _TRANSACTION_TTL_SECONDS)
    except ClaimStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="OAuth claim store unavailable") from exc

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

    # Consume BEFORE contacting the provider. Ambiguous provider outcomes cannot
    # be retried with the same authorization code or state.
    from backend.pollinations_oauth_claim_store import consume, issue, ClaimStoreUnavailable
    try:
        claim = consume("pkce_state", state, _owner_user_id())
    except ClaimStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="OAuth claim store unavailable") from exc
    if claim is None or not isinstance(claim.get("verifier"), str):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    transaction = _OAuthTransaction(verifier=claim["verifier"], created_at=time.time(),
                                    return_to=claim.get("return_to"),
                                    owner_user_id=_owner_user_id())

    try:
        config = PollinationsOAuthConfig.from_env()
        payload = exchange_authorization_code(
            config,
            code=code,
            code_verifier=transaction.verifier,
        )
    except (RuntimeError, ValueError) as exc:
        # The state was consumed before exchange. Never retry ambiguous provider outcomes.
        raise HTTPException(
            status_code=502,
            detail="Pollinations token exchange failed. Please retry the connection.",
        ) from exc

    try:
        expires_in = strict_expires_in(payload)
        # Metadata verification does not grant spending authority.
        trusted_app_key_id = os.getenv("POLLINATIONS_TRUSTED_APP_KEY_ID", "")
        verified = verify_provider_token(
            payload["access_token"],
            client_id=config.client_id,
            trusted_app_key_id=trusted_app_key_id,
        )
    except GrantVerificationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Pollinations identity or grant verification failed.",
        ) from exc

    session_id = secrets.token_urlsafe(32)
    session = _OAuthSession(
        access_token=payload["access_token"],
        expires_at=time.time() + expires_in,
        scope=str(payload.get("scope", "")),
        owner_user_id=transaction.owner_user_id,
        provider_subject=verified["provider_subject"],
    )
    try:
        _persist_session(session_id, session)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not persist Pollinations session. Reconnect with a new OAuth flow.",
        ) from exc

    if transaction.return_to:
        handoff_code = secrets.token_urlsafe(32)
        try:
            issue("mobile_handoff", handoff_code, transaction.owner_user_id,
                  {"session_id": session_id}, _HANDOFF_TTL_SECONDS)
        except ClaimStoreUnavailable as exc:
            try:
                _delete_persisted_session(session_id)
            except RuntimeError:
                pass  # Do not expose the session credential on failed handoff.
            raise HTTPException(status_code=503, detail="OAuth handoff store unavailable") from exc
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
def pollinations_mobile_exchange(
    payload: MobileExchangeRequest,
    x_soloforge_authorization: str | None = Header(default=None),
) -> dict[str, object]:
    require_soloforge_session(x_soloforge_authorization)
    _cleanup()
    from backend.pollinations_oauth_claim_store import consume, ClaimStoreUnavailable
    try:
        handoff = consume("mobile_handoff", payload.code, _owner_user_id())
    except ClaimStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="OAuth claim store unavailable") from exc
    if handoff is None or not isinstance(handoff.get("session_id"), str):
        raise HTTPException(status_code=400, detail="Invalid or expired mobile handoff code.")

    session = _get_session(handoff["session_id"])
    if session is None or session.owner_user_id != _owner_user_id():
        raise HTTPException(status_code=401, detail="Pollinations session has expired.")

    return {
        "session_token": handoff["session_id"],
        "expires_at": int(session.expires_at),
        "scope": session.scope,
    }


@router.get("/status")
def pollinations_status(
    session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    authorization: str | None = Header(default=None),
    x_soloforge_authorization: str | None = Header(default=None),
) -> dict[str, object]:
    require_soloforge_session(x_soloforge_authorization)
    bearer_session_id = _session_id_from_authorization(authorization)
    session = _get_session(bearer_session_id or session_id)
    if session is None or session.owner_user_id != _owner_user_id():
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
    x_soloforge_authorization: str | None = Header(default=None),
) -> JSONResponse:
    require_soloforge_session(x_soloforge_authorization)
    resolved_session_id = _session_id_from_authorization(authorization) or session_id
    if resolved_session_id and (session := _get_session(resolved_session_id)) and session.owner_user_id == _owner_user_id():
        try:
            _delete_persisted_session(resolved_session_id)
        except RuntimeError as exc:
            # The persisted credential could be reloaded by another worker.
            # Do not acknowledge revocation until durable deletion succeeds.
            raise HTTPException(
                status_code=503,
                detail="Pollinations logout could not be confirmed. Retry logout.",
            ) from exc
        with _lock:
            _sessions.pop(resolved_session_id, None)
    response = JSONResponse({"connected": False})
    _clear_session_cookie(response)
    return response


def get_pollinations_access_token(session_id: str | None, owner_authorization: str | None = None) -> str | None:
    if not session_id:
        return None  # Preserve local-only generation without provider credentials.
    require_soloforge_session(owner_authorization)
    session = _get_session(session_id)
    return session.access_token if session and session.owner_user_id == _owner_user_id() else None


def get_pollinations_access_token_from_authorization(
    authorization: str | None,
    owner_authorization: str | None = None,
) -> str | None:
    session_id = _session_id_from_authorization(authorization)
    return get_pollinations_access_token(session_id, owner_authorization)
