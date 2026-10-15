from urllib.parse import parse_qs, urlparse

import pytest
import threading
from backend import pollinations_oauth_claim_store as claim_store
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.pollinations_oauth_router as router_module
import backend.asset_forge.main as asset_forge_main
from backend.asset_forge.main import app as asset_forge_app


@pytest.fixture(autouse=True)
def reset_oauth_state():
    with router_module._lock:
        router_module._transactions.clear()
        router_module._sessions.clear()
        router_module._handoffs.clear()
        router_module._login_tickets.clear()
    yield
    with router_module._lock:
        router_module._transactions.clear()
        router_module._sessions.clear()
        router_module._handoffs.clear()
        router_module._login_tickets.clear()


def _client(monkeypatch):
    # Shared synthetic claim service for offline route contracts.
    claims = {}
    claim_lock = threading.Lock()
    def issue(kind, secret, owner, data, ttl):
        with claim_lock:
            assert (kind, secret) not in claims
            claims[(kind, secret)] = (owner, dict(data))
    def consume(kind, secret, owner):
        with claim_lock:
            value = claims.get((kind, secret))
            if value is None or value[0] != owner:
                return None
            claims.pop((kind, secret))
            return dict(value[1])
    monkeypatch.setattr(claim_store, "issue", issue)
    monkeypatch.setattr(claim_store, "consume", consume)
    monkeypatch.setenv("POLLINATIONS_CLIENT_ID", "pk_test")
    monkeypatch.setenv("POLLINATIONS_TRUSTED_APP_KEY_ID", "internal-test-app-id")
    monkeypatch.setenv(
        "POLLINATIONS_REDIRECT_URI",
        "https://example.com/auth/pollinations/callback",
    )
    monkeypatch.setenv("POLLINATIONS_SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv(
        "POLLINATIONS_MOBILE_RETURN_TO",
        "soloforge://oauth/pollinations",
    )
    monkeypatch.setenv(
        "POLLINATIONS_WEB_RETURN_TO",
        "https://soloforge-ai-web.onrender.com/",
    )
    # Offline synthetic provider verification for successful OAuth contract paths.
    # Production verifier is unchanged and separately tested for fail-closed errors.
    def verified_synthetic_grant(token, *, client_id, trusted_app_key_id):
        assert token == "sk_test_secret_should_stay_server_side"
        assert client_id == "pk_test"
        assert trusted_app_key_id == "internal-test-app-id"
        return {"status": "METADATA_VERIFIED_SPENDING_BLOCKED", "provider_subject": "provider-owner"}

    monkeypatch.setattr(router_module, "verify_provider_token", verified_synthetic_grant)
    monkeypatch.setattr(router_module, "require_soloforge_session", lambda header: (_ for _ in ()).throw(HTTPException(status_code=401, detail="owner required")) if header != "Bearer test-owner" else None)
    app = FastAPI()
    app.include_router(router_module.router)
    return TestClient(app, base_url="https://testserver")


def _fake_exchange(*args, **kwargs):
    return {
        "access_token": "sk_test_secret_should_stay_server_side",
        "token_type": "bearer",
        "expires_in": 600,
        "scope": "profile usage",
    }


def _login_ticket(client):
    response = client.post("/auth/pollinations/login-ticket", headers={"X-SoloForge-Authorization": "Bearer test-owner"})
    assert response.status_code == 200
    return response.json()["ticket"]


def _start_mobile_login(client):
    login = client.get(
        "/auth/pollinations/login",
        params={
            "client": "mobile",
            "return_to": "soloforge://oauth/pollinations",
            "ticket": _login_ticket(client),
        },
        follow_redirects=False,
    )
    assert login.status_code == 302
    location = login.headers["location"]
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


def test_login_uses_pkce_and_sets_state_cookie(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/auth/pollinations/login", params={"ticket": _login_ticket(client)}, follow_redirects=False)

    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["client_id"] == ["pk_test"]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"]
    assert query["code_challenge"]
    assert "__Host-soloforge_oauth_state" in response.headers.get("set-cookie", "")


def test_mobile_return_url_is_allowlisted(monkeypatch):
    client = _client(monkeypatch)
    response = client.get(
        "/auth/pollinations/login",
        params={"client": "mobile", "return_to": "evilapp://steal", "ticket": _login_ticket(client)},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Unsupported mobile return URL" in response.text

def test_web_return_url_is_allowlisted(monkeypatch):
    client = _client(monkeypatch)
    valid = client.get(
        "/auth/pollinations/login",
        params={
            "client": "web",
            "return_to": "https://soloforge-ai-web.onrender.com/",
            "ticket": _login_ticket(client),
        },
        follow_redirects=False,
    )
    assert valid.status_code == 302

    invalid = client.get(
        "/auth/pollinations/login",
        params={"client": "web", "return_to": "https://evil.example/", "ticket": _login_ticket(client)},
        follow_redirects=False,
    )
    assert invalid.status_code == 400
    assert "Unsupported web return URL" in invalid.text


def test_web_callback_returns_one_time_handoff_to_app(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(router_module, "exchange_authorization_code", _fake_exchange)
    login = client.get(
        "/auth/pollinations/login",
        params={
            "client": "web",
            "return_to": "https://soloforge-ai-web.onrender.com/",
            "ticket": _login_ticket(client),
        },
        follow_redirects=False,
    )
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    callback = client.get(
        "/auth/pollinations/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    target = urlparse(callback.headers["location"])
    assert f"{target.scheme}://{target.netloc}{target.path}" == (
        "https://soloforge-ai-web.onrender.com/"
    )
    handoff_code = parse_qs(target.query)["code"][0]
    assert handoff_code
    assert "sk_test_secret" not in callback.headers["location"]



def test_callback_rejects_state_from_another_browser(monkeypatch):
    client_a = _client(monkeypatch)
    client_b = _client(monkeypatch)
    login = client_a.get("/auth/pollinations/login", params={"ticket": _login_ticket(client_a)}, follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    response = client_b.get(
        "/auth/pollinations/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "OAuth state does not match" in response.text


def test_mobile_handoff_exchange_is_one_time_and_uses_json_body(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(router_module, "exchange_authorization_code", _fake_exchange)

    state = _start_mobile_login(client)
    callback = client.get(
        "/auth/pollinations/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "sk_test_secret" not in callback.headers["location"]

    handoff_code = parse_qs(urlparse(callback.headers["location"]).query)["code"][0]
    exchange = client.post(
        "/auth/pollinations/mobile/exchange",
        json={"code": handoff_code},
        headers={"X-SoloForge-Authorization": "Bearer test-owner"},
    )
    assert exchange.status_code == 200
    body = exchange.json()
    assert body["session_token"]
    assert body["scope"] == "profile usage"
    assert "access_token" not in body
    assert "sk_test_secret" not in exchange.text

    replay = client.post(
        "/auth/pollinations/mobile/exchange",
        json={"code": handoff_code},
        headers={"X-SoloForge-Authorization": "Bearer test-owner"},
    )
    assert replay.status_code == 400
    assert "Invalid or expired mobile handoff code" in replay.text

    query_string_attempt = client.post(
        f"/auth/pollinations/mobile/exchange?code={handoff_code}",
    )
    assert query_string_attempt.status_code == 422


def test_bearer_session_status_and_logout(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(router_module, "exchange_authorization_code", _fake_exchange)

    state = _start_mobile_login(client)
    callback = client.get(
        "/auth/pollinations/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )
    handoff_code = parse_qs(urlparse(callback.headers["location"]).query)["code"][0]
    exchange = client.post(
        "/auth/pollinations/mobile/exchange",
        json={"code": handoff_code},
        headers={"X-SoloForge-Authorization": "Bearer test-owner"},
    )
    session_token = exchange.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}", "X-SoloForge-Authorization": "Bearer test-owner"}

    status = client.get("/auth/pollinations/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert "access_token" not in status.json()

    logout = client.post("/auth/pollinations/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json() == {"connected": False}

    after_logout = client.get("/auth/pollinations/status", headers=headers)
    assert after_logout.json() == {"connected": False}


def test_status_restores_persisted_session_after_backend_restart(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(router_module, "_supabase_config", lambda: ("https://example.invalid", "test-only"))
    persisted = router_module._OAuthSession(
        access_token="sk_persisted_secret",
        expires_at=router_module.time.time() + 600,
        scope="profile usage",
        owner_user_id=router_module._owner_user_id(),
        provider_subject="provider-owner",
    )
    monkeypatch.setattr(
        router_module,
        "_load_persisted_session",
        lambda session_id: persisted if session_id == "persisted-session" else None,
    )

    with router_module._lock:
        router_module._sessions.clear()

    response = client.get(
        "/auth/pollinations/status",
        headers={"Authorization": "Bearer persisted-session", "X-SoloForge-Authorization": "Bearer test-owner"},
    )

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["scope"] == "profile usage"
    assert "access_token" not in response.json()
    with router_module._lock:
        assert router_module._sessions["persisted-session"] == persisted


def test_oauth_transaction_consumed_on_ambiguous_exchange_failure(monkeypatch):
    client = _client(monkeypatch)

    def fail_exchange(*args, **kwargs):
        raise RuntimeError("temporary provider failure")

    monkeypatch.setattr(router_module, "exchange_authorization_code", fail_exchange)
    state = _start_mobile_login(client)

    response = client.get(
        "/auth/pollinations/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 502
    assert "Please retry the connection" in response.text
    replay = client.get("/auth/pollinations/callback",
                        params={"code": "oauth-code", "state": state}, follow_redirects=False)
    assert replay.status_code == 400


def test_ceo_missing_master_fails_closed_without_pollinations_session(monkeypatch):
    monkeypatch.setattr(asset_forge_main, "_load_character_reference", lambda _: None)
    client = TestClient(asset_forge_app)
    response = client.post(
        "/v1/asset-forge/generate",
        json={
            "character": "CEO",
            "product": "Sticker",
            "theme": "Healing & Encouragement",
            "style": "Cute 3D Chibi",
            "quantity": 4,
            "messages": [],
        },
    )

    assert response.status_code == 409
    assert "master reference is missing" in response.json()["detail"]


def test_noncanonical_character_uses_local_fallback_without_pollinations_session(monkeypatch):
    monkeypatch.setattr(asset_forge_main, "_load_character_reference", lambda _: None)
    client = TestClient(asset_forge_app)
    response = client.post(
        "/v1/asset-forge/generate",
        json={
            "character": "Cat",
            "product": "Sticker",
            "theme": "Healing & Encouragement",
            "style": "Cute 3D Chibi",
            "quantity": 4,
            "messages": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["generation_mode"] == "local_fallback"
    assert len(body["files"]) == 4
    assert body["source_image_base64"]
    assert body["zip_base64"]


def test_owner_ticket_is_required_and_single_use(monkeypatch):
    client = _client(monkeypatch)
    denied = client.get("/auth/pollinations/login", follow_redirects=False)
    assert denied.status_code == 401
    ticket = _login_ticket(client)
    ok = client.get("/auth/pollinations/login", params={"ticket": ticket}, follow_redirects=False)
    assert ok.status_code == 302
    replay = client.get("/auth/pollinations/login", params={"ticket": ticket}, follow_redirects=False)
    assert replay.status_code == 401


def test_cross_user_handoff_and_session_denied(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(router_module, "exchange_authorization_code", _fake_exchange)
    state = _start_mobile_login(client)
    callback = client.get("/auth/pollinations/callback", params={"code": "oauth-code", "state": state}, follow_redirects=False)
    code = parse_qs(urlparse(callback.headers["location"]).query)["code"][0]
    denied = client.post("/auth/pollinations/mobile/exchange", json={"code": code}, headers={"X-SoloForge-Authorization": "Bearer other-user"})
    assert denied.status_code != 200
    exchanged = client.post("/auth/pollinations/mobile/exchange", json={"code": code}, headers={"X-SoloForge-Authorization": "Bearer test-owner"})
    assert exchanged.status_code == 200
    session = exchanged.json()["session_token"]
    denied_status = client.get("/auth/pollinations/status", headers={"Authorization": f"Bearer {session}", "X-SoloForge-Authorization": "Bearer other-user"})
    assert denied_status.status_code != 200


def test_logout_storage_failure_does_not_claim_revocation(monkeypatch):
    client = _client(monkeypatch)
    session_id = "synthetic-revocation-session"
    session = router_module._OAuthSession(
        access_token="synthetic-provider-token",
        expires_at=router_module.time.time() + 600,
        scope="profile usage",
        owner_user_id=router_module._owner_user_id(),
        provider_subject="provider-owner",
    )
    with router_module._lock:
        router_module._sessions[session_id] = session

    def unavailable(_session_id):
        assert _session_id == session_id
        raise RuntimeError("synthetic storage outage")

    monkeypatch.setattr(router_module, "_delete_persisted_session", unavailable)
    headers = {
        "Authorization": f"Bearer {session_id}",
        "X-SoloForge-Authorization": "Bearer test-owner",
    }
    logout = client.post("/auth/pollinations/logout", headers=headers)
    assert logout.status_code == 503
    assert "could not be confirmed" in logout.json()["detail"]
    with router_module._lock:
        assert router_module._sessions[session_id] == session


def test_shared_store_revocation_invalidates_cached_session_across_workers(monkeypatch):
    """A second worker must not serve a cached credential after durable logout."""
    client = _client(monkeypatch)
    session_id = "synthetic-cross-worker"
    session = router_module._OAuthSession(
        access_token="synthetic-access-token",
        expires_at=router_module.time.time() + 600,
        scope="profile",
        owner_user_id=router_module._owner_user_id(),
        provider_subject="synthetic-subject",
    )
    persisted = {session_id: session}
    monkeypatch.setattr(router_module, "_supabase_config", lambda: ("https://example.invalid", "test-only"))
    monkeypatch.setattr(router_module, "_load_persisted_session", lambda sid: persisted.get(sid))
    monkeypatch.setattr(router_module, "_delete_persisted_session", lambda sid: persisted.pop(sid, None))
    with router_module._lock:
        router_module._sessions[session_id] = session

    headers = {"Authorization": f"Bearer {session_id}", "X-SoloForge-Authorization": "Bearer test-owner"}
    assert client.get("/auth/pollinations/status", headers=headers).json()["connected"] is True
    assert client.post("/auth/pollinations/logout", headers=headers).status_code == 200

    # Simulate stale in-memory state retained by a different process.
    with router_module._lock:
        router_module._sessions[session_id] = session
    assert client.get("/auth/pollinations/status", headers=headers).json()["connected"] is False
    assert router_module.get_pollinations_access_token(session_id, "Bearer test-owner") is None


def test_shared_store_outage_denies_cached_access_token(monkeypatch):
    _client(monkeypatch)  # Install synthetic owner-session verifier.
    session_id = "synthetic-outage"
    session = router_module._OAuthSession(
        access_token="synthetic-access-token",
        expires_at=router_module.time.time() + 600,
        scope="profile",
        owner_user_id=router_module._owner_user_id(),
        provider_subject="synthetic-subject",
    )
    monkeypatch.setattr(router_module, "_supabase_config", lambda: ("https://example.invalid", "test-only"))
    def unavailable(_sid):
        raise RuntimeError("synthetic storage outage")
    monkeypatch.setattr(router_module, "_load_persisted_session", unavailable)
    with router_module._lock:
        router_module._sessions[session_id] = session
    assert router_module.get_pollinations_access_token(session_id, "Bearer test-owner") is None
