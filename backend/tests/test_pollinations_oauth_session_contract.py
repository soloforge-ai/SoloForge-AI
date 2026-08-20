from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.pollinations_oauth_router as router_module
from backend.asset_forge.main import app as asset_forge_app


@pytest.fixture(autouse=True)
def reset_oauth_state():
    with router_module._lock:
        router_module._transactions.clear()
        router_module._sessions.clear()
        router_module._handoffs.clear()
    yield
    with router_module._lock:
        router_module._transactions.clear()
        router_module._sessions.clear()
        router_module._handoffs.clear()


def _client(monkeypatch):
    monkeypatch.setenv("POLLINATIONS_CLIENT_ID", "pk_test")
    monkeypatch.setenv(
        "POLLINATIONS_REDIRECT_URI",
        "https://example.com/auth/pollinations/callback",
    )
    monkeypatch.setenv("POLLINATIONS_SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv(
        "POLLINATIONS_MOBILE_RETURN_TO",
        "soloforge://oauth/pollinations",
    )
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


def _start_mobile_login(client):
    login = client.get(
        "/auth/pollinations/login",
        params={
            "client": "mobile",
            "return_to": "soloforge://oauth/pollinations",
        },
        follow_redirects=False,
    )
    assert login.status_code == 302
    location = login.headers["location"]
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


def test_login_uses_pkce_and_sets_state_cookie(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/auth/pollinations/login", follow_redirects=False)

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
        params={"client": "mobile", "return_to": "evilapp://steal"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Unsupported mobile return URL" in response.text


def test_callback_rejects_state_from_another_browser(monkeypatch):
    client_a = _client(monkeypatch)
    client_b = _client(monkeypatch)
    login = client_a.get("/auth/pollinations/login", follow_redirects=False)
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
    )
    session_token = exchange.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    status = client.get("/auth/pollinations/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert "access_token" not in status.json()

    logout = client.post("/auth/pollinations/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json() == {"connected": False}

    after_logout = client.get("/auth/pollinations/status", headers=headers)
    assert after_logout.json() == {"connected": False}


def test_asset_generation_requires_connected_pollinations_session():
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
    assert response.status_code == 401
    assert response.json()["detail"] == "Connect Pollinations before generating assets."
