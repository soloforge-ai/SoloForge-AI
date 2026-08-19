from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.pollinations_oauth_router as router_module


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("POLLINATIONS_CLIENT_ID", "pk_test")
    monkeypatch.setenv(
        "POLLINATIONS_REDIRECT_URI",
        "https://example.com/auth/pollinations/callback",
    )
    monkeypatch.setenv("POLLINATIONS_SESSION_COOKIE_SECURE", "true")
    app = FastAPI()
    app.include_router(router_module.router)
    return TestClient(app)


def test_login_creates_pkce_state_and_redirect(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/auth/pollinations/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    assert query["client_id"] == ["pk_test"]
    assert query["redirect_uri"] == [
        "https://example.com/auth/pollinations/callback"
    ]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"]
    assert query["code_challenge"]
    assert "__Host-soloforge_oauth_state" in response.headers.get("set-cookie", "")


def test_callback_rejects_unknown_state(monkeypatch):
    client = _client(monkeypatch)
    response = client.get(
        "/auth/pollinations/callback?code=oauth-code&state=unknown",
    )

    assert response.status_code == 400
    assert "OAuth state does not match" in response.text


def test_callback_rejects_state_from_another_browser(monkeypatch):
    client_a = _client(monkeypatch)
    client_b = _client(monkeypatch)
    login = client_a.get("/auth/pollinations/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    response = client_b.get(
        f"/auth/pollinations/callback?code=oauth-code&state={state}",
    )
    assert response.status_code == 400
    assert "OAuth state does not match" in response.text


def test_callback_stores_token_server_side(monkeypatch):
    client = _client(monkeypatch)
    login = client.get("/auth/pollinations/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    def fake_exchange(config, *, code, code_verifier, timeout=30):
        assert code == "oauth-code"
        assert code_verifier
        return {
            "access_token": "sk_test_secret_should_never_be_returned",
            "token_type": "bearer",
            "expires_in": 600,
            "scope": "profile usage",
        }

    monkeypatch.setattr(router_module, "exchange_authorization_code", fake_exchange)

    callback = client.get(
        f"/auth/pollinations/callback?code=oauth-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "sk_test_secret" not in callback.headers.get("location", "")

    status = client.get("/auth/pollinations/status")
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert "access_token" not in status.json()
    assert "sk_test_secret" not in status.text


def test_logout_invalidates_session(monkeypatch):
    client = _client(monkeypatch)
    login = client.get("/auth/pollinations/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    monkeypatch.setattr(
        router_module,
        "exchange_authorization_code",
        lambda *args, **kwargs: {
            "access_token": "sk_test",
            "expires_in": 600,
            "scope": "profile usage",
        },
    )
    client.get(
        f"/auth/pollinations/callback?code=oauth-code&state={state}",
        follow_redirects=False,
    )
    assert client.get("/auth/pollinations/status").json()["connected"] is True

    logout = client.post("/auth/pollinations/logout")
    assert logout.status_code == 200
    assert client.get("/auth/pollinations/status").json() == {"connected": False}
