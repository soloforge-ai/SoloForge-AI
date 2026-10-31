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
from dataclasses import dataclass, field
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

from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError


class _PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            try:
                response = await original(request)
            except RequestValidationError:
                response = JSONResponse({"detail": "Invalid request."}, status_code=422)
            except HTTPException as exc:
                response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        return handler


router = APIRouter(route_class=_PrivateRoute, prefix="/auth/pollinations", tags=["pollinations-auth"])
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
    owner_id: str | None = None
    owner_authorization: str | None = field(default=None, repr=False)


@dataclass
class _OAuthSession:
    access_token: str = field(repr=False)
    expires_at: float
    scope: str
    submitted_by_owner: str | None = None
    verification_status: str = "PENDING_VERIFICATION"
    provider_subject: str | None = None


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
_launches: dict[str, tuple[str, str, float]] = {}


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
        # Status only: response bodies can contain credential-bearing row details.
        print("supabase_session_store_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("Supabase session store is unavailable.") from None
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
        raise RuntimeError("Credential store unavailable")

    expires_at = datetime.fromtimestamp(session.expires_at, tz=timezone.utc).isoformat()
    _supabase_request(
        "POST",
        "pollinations_sessions?on_conflict=session_id",
        body={
            "session_id": session_id,
            "access_token": session.access_token,
            "token_type": "Bearer",
            "scope": _public_scope(session.scope),
            "submitted_by_owner": session.submitted_by_owner,
            "verification_status": session.verification_status,
            "provider_subject": session.provider_subject,
            "provider_ownership_verified": session.verification_status == "VERIFIED",
            "spending_authorized": False,
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
        f"?session_id=eq.{encoded}&select=access_token,expires_at,scope,submitted_by_owner,verification_status,provider_subject&limit=1",
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
        return None

    token = str(row.get("access_token") or "")
    if not token:
        return None

    return _OAuthSession(
        access_token=token,
        expires_at=expires_at,
        scope=str(row.get("scope") or ""),
        submitted_by_owner=row.get("submitted_by_owner"),
        verification_status=row.get("verification_status", "PENDING_VERIFICATION"),
        provider_subject=row.get("provider_subject"),
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
        for ticket, launch in list(_launches.items()):
            if now - launch[2] > 120:
                _launches.pop(ticket, None)
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


@router.get("/login")
def pollinations_login(
    client: str | None = Query(default=None),
    return_to: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> RedirectResponse:
    owner_id = _owner(authorization)
    try:
        config = PollinationsOAuthConfig.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if config.authorize_url != "https://enter.pollinations.ai/authorize" or config.token_url != "https://enter.pollinations.ai/api/oauth/token":
        raise HTTPException(503, "Unsupported provider endpoint configuration.")
    if client not in (None, "mobile", "web"):
        raise HTTPException(400, "Unsupported OAuth client.")
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

    verifier, challenge, state = create_pkce_transaction()
    with _lock:
        _transactions[state] = _OAuthTransaction(
            verifier=verifier,
            created_at=time.time(),
            return_to=resolved_return_to,
            owner_id=owner_id,
            owner_authorization=authorization,
        )

    authorization_url = build_authorization_url(
        config,
        code_challenge=challenge,
        state=state,
    )
    response = RedirectResponse(url=authorization_url, status_code=302)
    _set_state_cookie(response, state)
    return response


class ConnectRequest(BaseModel):
    client: str
    return_to: str


@router.post("/connect")
def pollinations_connect(payload: ConnectRequest,
    authorization: str | None = Header(default=None)) -> dict:
    _cleanup()
    response = pollinations_login(payload.client, payload.return_to, authorization)
    url = response.headers["location"]
    state = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["state"][0]
    ticket = secrets.token_urlsafe(32)
    with _lock:
        _launches[ticket] = (url, state, time.time())
    return {"launch_path": "/auth/pollinations/launch?ticket=" + ticket, "expires_in": 120}


@router.get("/launch")
def pollinations_launch(ticket: str) -> RedirectResponse:
    with _lock:
        launch = _launches.pop(ticket, None)
    if launch is None or time.time() - launch[2] > 120:
        raise HTTPException(400, "Connection expired. Start again.")
    response = RedirectResponse(launch[0], status_code=302)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    _set_state_cookie(response, launch[1])
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
    # Validate the original owner session, not callback headers. This preserves
    # browser redirects while rejecting revoked sessions and owner mismatches
    # before any provider token exchange or credential persistence.
    if _owner(transaction.owner_authorization) != transaction.owner_id:
        raise HTTPException(403, "Owner identity changed. Start again.")

    try:
        config = PollinationsOAuthConfig.from_env()
        if config.token_url != "https://enter.pollinations.ai/api/oauth/token":
            raise RuntimeError("Unsupported provider token endpoint")
        payload = exchange_authorization_code(
            config,
            code=code,
            code_verifier=transaction.verifier,
        )
    except (RuntimeError, ValueError) as exc:
        # Exchange may have consumed the provider code. Never retry ambiguous exchange.
        raise HTTPException(
            status_code=502,
            detail="Pollinations token exchange failed. Please retry the connection.",
        ) from exc

    with _lock:
        _transactions.pop(state, None)

    session_id = secrets.token_urlsafe(32)
    # The provider omits expires_in for keys without a configured expiry.
    # Use a bounded local verification window; never infer unlimited execution.
    expires_in = payload.get("expires_in")
    if expires_in is None:
        expires_in = 600
    if not isinstance(expires_in, int) or isinstance(expires_in, bool) or expires_in <= 0:
        raise HTTPException(502, "Invalid credential expiry.")
    session = _OAuthSession(
        access_token=payload.get("access_token"),
        expires_at=time.time() + expires_in,
        scope=str(payload.get("scope", "")),
        submitted_by_owner=transaction.owner_id,
    )
    if not transaction.owner_id or not isinstance(session.access_token, str) or not session.access_token.startswith("sk_"):
        raise HTTPException(502, "Invalid owner-bound credential response.")
    # OAuth code/PKCE plus authenticated Owner V2 establishes independent proof.
    # A standalone submitted SK never enters this binding path.
    # OAuth connectivity is not proof of owner binding. Preserve the existing
    # pending-session contract when independent identity evidence is unavailable;
    # verification remains fail-closed until a separate trusted binding succeeds.
    try:
        _bind_oauth_owner_subject(transaction.owner_id, session.access_token)
    except HTTPException:
        pass
    try:
        _persist_session(session_id, session)
    except RuntimeError as exc:
        with _lock:
            _sessions.pop(session_id, None)
        raise HTTPException(
            status_code=503,
            detail="Could not persist Pollinations session. Please try again.",
        ) from exc

    with _lock:
        _sessions[session_id] = session

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
def pollinations_mobile_exchange(payload: MobileExchangeRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    owner_id = _owner(authorization)
    _cleanup()
    with _lock:
        handoff = _handoffs.pop(payload.code, None)
    if handoff is None:
        raise HTTPException(status_code=400, detail="Invalid or expired mobile handoff code.")

    session = _get_session(handoff.session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Pollinations session has expired.")

    _check_owner(session, owner_id)
    return {
        "verification_status": session.verification_status,
        "spending_authorized": False,
        "session_token": handoff.session_id,
        "expires_at": int(session.expires_at),
        "scope": _public_scope(session.scope),
    }


@router.get("/status")
def pollinations_status(
    session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    authorization: str | None = Header(default=None),
    pollinations_session: str | None = Header(default=None, alias="X-Pollinations-Session"),
) -> dict[str, object]:
    owner_id = _owner(authorization)
    session = _get_session(pollinations_session or session_id)
    if session is None:
        return {"connected": False}
    _check_owner(session, owner_id)
    return {
        "verification_status": session.verification_status,
        "spending_authorized": False,
        "connected": True,
        "expires_at": int(session.expires_at),
        "scope": _public_scope(session.scope),
    }


def _public_scope(value) -> str:
    return value[:256] if isinstance(value, str) and "sk_" not in value and "Bearer " not in value else ""


def _owner(authorization: str | None) -> str:
    """Only the live V2 registry establishes the canonical Owner ID."""
    from .owner_v2 import OwnerV2, Unauthorized, Unavailable
    try:
        return OwnerV2().authenticate(authorization)["owner_id"]
    except Unauthorized:
        raise HTTPException(401, "Owner V2 sign-in required.") from None
    except Unavailable:
        raise HTTPException(503, "Owner V2 unavailable.") from None


def _check_owner(session: _OAuthSession, owner_id: str) -> None:
    if session.submitted_by_owner != owner_id:
        raise HTTPException(404, "Credential unavailable.")


def _rows(path: str) -> list[dict]:
    if _supabase_config() is None:
        raise HTTPException(503, "Credential store unavailable.")
    try:
        raw = _supabase_request("GET", path)
        rows = json.loads(raw) if raw else []
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError()
        return rows
    except (RuntimeError, ValueError, TypeError, UnicodeError):
        raise HTTPException(503, "Credential store unavailable.") from None


def _bind_oauth_owner_subject(owner_id: str, oauth_token: str) -> str:
    """Bind an independently completed OAuth code/PKCE login, never an SK submission.

    Existing verified bindings are immutable here. An absent or conflicting owner
    account fails closed; no owner account is auto-created from provider data.
    """
    from .pollinations_sk_lifecycle import _userinfo
    status, payload = _userinfo(oauth_token)
    subject = payload.get("sub") if isinstance(payload, dict) else None
    if (status != 200 or not isinstance(subject, str) or not subject.strip()
            or len(subject) > 512 or "sk_" in subject or "Bearer " in subject):
        raise HTTPException(503, "Independent Pollinations OAuth identity unavailable.")
    owner = urllib.parse.quote(owner_id, safe="")
    path = "soloforge_owner_accounts?owner_id=eq." + owner + "&provider=eq.pollinations"
    rows = _rows(path + "&select=provider_account_id,verification_status,verification_evidence,verified_at&limit=1")
    if len(rows) != 1:
        raise HTTPException(409, "Pollinations owner account registration required.")
    previous = rows[0]
    if previous.get("verification_status") == "verified":
        if (previous.get("provider_account_id") != subject
                or not previous.get("verification_evidence") or not previous.get("verified_at")):
            raise HTTPException(409, "Conflicting verified Pollinations owner binding.")
        return subject
    if previous.get("verification_status") != "pending":
        raise HTTPException(409, "Pollinations owner account requires manual review.")
    # Conditional update is the concurrency gate. Never overwrite a verified row.
    # Evidence records the OAuth proof type, not the access token or authorization code.
    try:
        raw = _supabase_request("PATCH", path + "&verification_status=eq.pending",
            body={"provider_account_id": subject, "verification_status": "verified",
                  "verification_evidence": "pollinations_oauth_code_pkce_userinfo_v1",
                  "verified_at": datetime.now(tz=timezone.utc).isoformat()},
            prefer="return=representation")
        updated = json.loads(raw) if raw else []
    except (RuntimeError, ValueError, TypeError):
        raise HTTPException(503, "Pollinations owner binding persistence unavailable.") from None
    if not isinstance(updated, list) or len(updated) != 1 or updated[0].get("provider_account_id") != subject:
        raise HTTPException(409, "Pollinations owner binding changed; reconnect or review.")
    return subject


def _expected_subject(owner_id: str) -> str | None:
    rows = _rows("soloforge_owner_accounts?owner_id=eq." + urllib.parse.quote(owner_id, safe="")
        + "&provider=eq.pollinations&verification_status=eq.verified"
        + "&select=provider_account_id,verification_evidence,verified_at&limit=1")
    if not rows:
        return None
    row = rows[0]
    subject = row.get("provider_account_id")
    if not row.get("verification_evidence") or not row.get("verified_at"):
        return None
    return subject if isinstance(subject, str) and subject.strip() else None


def _record_id(value: str) -> str:
    from uuid import UUID
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Invalid credential record ID.") from None


def _existing_pollinations_session(record_id: str | None, owner_id: str) -> _OAuthSession:
    if not record_id:
        raise HTTPException(400, "Select an owner-scoped credential.")
    rows = _rows("pollinations_sessions?id=eq." + _record_id(record_id)
        + "&submitted_by_owner=eq." + urllib.parse.quote(owner_id, safe="")
        + "&select=access_token,expires_at,scope,submitted_by_owner,verification_status,provider_subject&limit=1")
    if not rows:
        raise HTTPException(404, "Credential unavailable.")
    row = rows[0]
    try:
        session = _OAuthSession(row["access_token"], datetime.fromisoformat(
            row["expires_at"].replace("Z", "+00:00")).timestamp(), row.get("scope", ""),
            row.get("submitted_by_owner"), row.get("verification_status", "PENDING_VERIFICATION"),
            row.get("provider_subject"))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise HTTPException(503, "Invalid credential record.") from None
    _check_owner(session, owner_id)
    return session


def _credential(owner_id, session_id, record_id):
    if session_id:
        session = _get_session(session_id)
        if session is None:
            raise HTTPException(404, "Credential unavailable.")
        _check_owner(session, owner_id)
        return session
    return _existing_pollinations_session(record_id, owner_id)


@router.get("/account/credentials")
def pollinations_credential_choices(authorization: str | None = Header(default=None)) -> dict:
    owner_id = _owner(authorization)
    rows = _rows("pollinations_sessions?submitted_by_owner=eq."
        + urllib.parse.quote(owner_id, safe="")
        + "&select=id,expires_at,scope,verification_status&order=updated_at.desc&limit=50")
    return {"credentials": [{**{k: r.get(k) for k in ("id", "expires_at", "verification_status")}, "scope": _public_scope(r.get("scope"))}
        for r in rows], "spending_authorized": False}


@router.get("/account/inspect")
def pollinations_account_inspect(
    authorization: str | None = Header(default=None),
    pollinations_session: str | None = Header(default=None, alias="X-Pollinations-Session"),
    credential_record_id: str | None = Query(default=None),
) -> dict:
    from backend.pollinations_account_inspect import inspect_account
    owner_id = _owner(authorization)
    session = _credential(owner_id, pollinations_session, credential_record_id)
    if session.expires_at <= time.time():
        return {"state": "UNKNOWN", "reason": "session_expired", "spending_authorized": False}
    evidence = inspect_account(session.access_token)
    verified = (session.verification_status == "VERIFIED"
        and bool(session.provider_subject)
        and evidence.get("provider_subject") == session.provider_subject
        and session.provider_subject == _expected_subject(owner_id))
    return {**evidence, "owner_binding": "VERIFIED" if verified else "UNVERIFIED",
            "verification_status": "VERIFIED" if verified else "PENDING_VERIFICATION",
            "provider_ownership_verified": verified, "spending_authorized": False}


@router.get("/sk/preflight")
def pollinations_sk_preflight(
    authorization: str | None = Header(default=None),
    pollinations_session: str | None = Header(default=None, alias="X-Pollinations-Session"),
    credential_record_id: str | None = Query(default=None),
) -> dict:
    from backend.pollinations_sk_lifecycle import verify_identity
    owner_id = _owner(authorization)
    session = _credential(owner_id, pollinations_session, credential_record_id)
    return verify_identity(session.access_token, session.expires_at, _expected_subject(owner_id))


@router.get("/sk/identity-diagnostic")
def pollinations_sk_identity_diagnostic(
    authorization: str | None = Header(default=None),
    pollinations_session: str | None = Header(default=None, alias="X-Pollinations-Session"),
    credential_record_id: str | None = Query(default=None),
) -> dict:
    """Read-only identity comparison. Never changes credential or spending state."""
    from backend.pollinations_sk_lifecycle import _userinfo
    owner_id = _owner(authorization)
    session = _credential(owner_id, pollinations_session, credential_record_id)
    result = {"comparison": "UNKNOWN", "spending_authorized": False,
              "owner_binding": "UNVERIFIED"}
    if session.expires_at <= time.time():
        return {**result, "reason": "session_expired"}
    if not isinstance(session.access_token, str) or not session.access_token.startswith("sk_"):
        return {**result, "reason": "credential_invalid"}
    expected = os.getenv("POLLINATIONS_TRUSTED_APP_KEY_ID", "").strip()
    if not expected:
        return {**result, "reason": "reference_missing"}
    status, payload = _userinfo(session.access_token)
    if status != 200 or not isinstance(payload, dict):
        return {**result, "reason": "userinfo_unavailable"}
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 512:
        return {**result, "reason": "provider_subject_missing"}
    return {**result, "comparison": "MATCH" if secrets.compare_digest(subject, expected)
            else "MISMATCH"}


class ReverificationRequest(BaseModel):
    credential_record_id: str


@router.post("/sk/reverify")
def pollinations_reverify(payload: ReverificationRequest,
    authorization: str | None = Header(default=None)) -> dict:
    from backend.pollinations_sk_lifecycle import verify_identity
    owner_id = _owner(authorization)
    record_id = _record_id(payload.credential_record_id)
    session = _existing_pollinations_session(record_id, owner_id)
    result = verify_identity(session.access_token, session.expires_at, _expected_subject(owner_id))
    # Failed evidence never promotes or preserves a stale verified status.
    try:
        raw = _supabase_request("POST", "rpc/pollinations_reverify", body={
            "p_owner_id": owner_id, "p_record_id": record_id,
            "p_subject": result.get("provider_subject"),
            "p_identity_verified": result["provider_ownership_verified"],
        })
        persisted = json.loads(raw) if raw else None
        if not isinstance(persisted, dict) or persisted.get("verification_status") not in ("VERIFIED", "PENDING_VERIFICATION") or not isinstance(persisted.get("provider_ownership_verified"), bool) or persisted.get("spending_authorized") is not False:
            raise RuntimeError()
    except (RuntimeError, ValueError, TypeError):
        raise HTTPException(503, "Verification persistence unconfirmed; reload before retry.") from None
    # Invalidate local views; a persisted reload is authoritative.
    with _lock:
        _sessions.clear()
    outcome = ("VERIFIED" if persisted["provider_ownership_verified"] else
        "REJECTED" if result.get("verification_outcome") == "REJECTED" else "UNKNOWN")
    return {"verification_outcome": outcome, **{k: persisted.get(k) for k in ("verification_status", "provider_ownership_verified", "provider_subject", "spending_authorized")},
            **({"reason": result["reason"]} if "reason" in result else {})}


class ClaimRequest(BaseModel):
    credential_record_id: str
    access_token: str = Field(min_length=4, max_length=4096, pattern=r"^sk_[A-Za-z0-9_-]+$", repr=False)


class SubmitRequest(BaseModel):
    access_token: str = Field(min_length=4, max_length=4096, pattern=r"^sk_[A-Za-z0-9_-]+$", repr=False)


@router.post("/sk/submit")
def pollinations_submit(payload: SubmitRequest,
    authorization: str | None = Header(default=None)) -> dict:
    owner_id = _owner(authorization)
    session_id = secrets.token_urlsafe(32)
    # A short local verification window is not a claim about the key's provider expiry.
    session = _OAuthSession(payload.access_token, time.time() + 600, "", owner_id)
    try:
        _persist_session(session_id, session)
    except RuntimeError:
        raise HTTPException(409, "Credential could not be submitted; use the claim flow for an existing record.") from None
    return {"verification_status": "PENDING_VERIFICATION", "provider_ownership_verified": False,
            "spending_authorized": False}


@router.post("/sk/claim")
def pollinations_claim(payload: ClaimRequest,
    authorization: str | None = Header(default=None)) -> dict:
    """Admit a legacy credential to Pending using Owner V2 and secret possession.

    Independent provider evidence is required only by the reverification path.

    No legacy list or record-secret lookup is exposed. The conditional update is
    atomic across contenders and cannot reassign an already claimed credential.
    """
    owner_id = _owner(authorization)
    record_id = _record_id(payload.credential_record_id)
    rows = _rows("pollinations_sessions?id=eq." + record_id
        + "&submitted_by_owner=is.null&select=access_token,expires_at,owner_user_id,provider_subject&limit=1")
    if not rows or not secrets.compare_digest(str(rows[0].get("access_token", "")), payload.access_token):
        raise HTTPException(404, "Credential unavailable.")
    legacy_owner = rows[0].get("owner_user_id")
    if legacy_owner:
        accounts = _rows("soloforge_owner_accounts?owner_id=eq." + urllib.parse.quote(owner_id, safe="")
            + "&provider=eq.supabase&verification_status=eq.verified"
            + "&select=provider_account_id,verification_evidence,verified_at&limit=1")
        if not accounts or accounts[0].get("provider_account_id") != legacy_owner or not accounts[0].get("verification_evidence") or not accounts[0].get("verified_at"):
            raise HTTPException(404, "Credential unavailable.")
    try:
        raw = _supabase_request("PATCH", "pollinations_sessions?id=eq." + record_id
            + "&submitted_by_owner=is.null&owner_user_id="
            + ("eq." + urllib.parse.quote(legacy_owner, safe="") if legacy_owner else "is.null"), body={"submitted_by_owner": owner_id,
                "verification_status": "PENDING_VERIFICATION", "provider_ownership_verified": False,
                "provider_subject": rows[0].get("provider_subject") if legacy_owner else None, "spending_authorized": False}, prefer="return=representation")
        changed = json.loads(raw) if raw else []
        if (not isinstance(changed, list) or len(changed) != 1
            or not isinstance(changed[0], dict)
            or changed[0].get("id") != record_id
            or changed[0].get("submitted_by_owner") != owner_id
            or changed[0].get("verification_status") != "PENDING_VERIFICATION"
            or changed[0].get("provider_ownership_verified") is not False
            or changed[0].get("spending_authorized") is not False):
            raise RuntimeError()
    except (RuntimeError, ValueError, TypeError):
        raise HTTPException(409, "Claim unconfirmed; reload credential list.") from None
    return {"verification_status": "PENDING_VERIFICATION", "provider_ownership_verified": False,
            "spending_authorized": False}


@router.post("/logout")
def pollinations_logout(
    session_id: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    authorization: str | None = Header(default=None),
    pollinations_session: str | None = Header(default=None, alias="X-Pollinations-Session"),
) -> JSONResponse:
    owner_id = _owner(authorization)
    resolved_session_id = pollinations_session or session_id
    if resolved_session_id:
        session = _get_session(resolved_session_id)
        if session is None:
            raise HTTPException(404, "Credential unavailable.")
        _check_owner(session, owner_id)
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
    # Connecting/verifying a credential never grants execution authority.
    # Do not load a credential through the legacy execution shortcut.
    return None


def get_pollinations_access_token_from_authorization(
    authorization: str | None,
) -> str | None:
    session_id = _session_id_from_authorization(authorization)
    return get_pollinations_access_token(session_id)
