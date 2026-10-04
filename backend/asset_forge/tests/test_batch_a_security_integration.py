"""HTTP-level Batch A contract with all outbound dependencies isolated.

No production URL, credential, job ID, worker, publisher or Telegram API is used.
"""
from __future__ import annotations

import io
import json
import socket
import time
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

from backend.asset_forge import main
from backend import content_jobs_api, soloforge_session as auth

OWNER = "72112ead-d399-4a40-aa51-ee17811cb10d"
ANONYMOUS = "00000000-0000-4000-8000-000000000001"
NON_OWNER = "00000000-0000-4000-8000-000000000002"
FAKE_ROW = {"id": "fixture-only-job", "status": "READY_FOR_REVIEW"}


@pytest.fixture
def isolated_api(monkeypatch):
    # Overwrite even if a developer has production settings in their shell.
    for key in (
        "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET",
        "PUBLORA_API_KEY", "PUBLORA_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://auth-fixture.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "fixture-publishable")
    monkeypatch.setenv("SOLOFORGE_SESSION_SECRET", "fixture-only-signing-secret-0123456789")
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", OWNER)
    monkeypatch.setenv("SOLOFORGE_SESSION_TTL_SECONDS", "900")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "false")
    monkeypatch.delenv("SOLOFORGE_SESSION_NOT_BEFORE", raising=False)

    calls = {"auth": [], "db": [], "workers": []}
    identities = {
        "owner-supabase": (OWNER, ["github"], False),
        "anonymous-supabase": (ANONYMOUS, ["anonymous"], True),
        "nonowner-supabase": (NON_OWNER, ["github"], False),
        "owner-wrong-provider": (OWNER, ["email"], False),
    }

    def fake_auth(request, timeout):
        assert request.full_url == "https://auth-fixture.invalid/auth/v1/user"
        assert timeout == 10
        headers = {key.lower(): value for key, value in request.header_items()}
        assert headers.get("apikey") == "fixture-publishable"
        bearer = headers.get("authorization", "")
        calls["auth"].append(bearer)
        identity = identities.get(bearer.removeprefix("Bearer "))
        if identity is None:
            raise urllib.error.HTTPError(request.full_url, 401, "invalid", {}, None)
        user_id, providers, anonymous = identity
        return io.BytesIO(json.dumps({
            "id": user_id,
            "is_anonymous": anonymous,
            "app_metadata": {"providers": providers},
        }).encode())

    def fake_db(method, path, **kwargs):
        # Every DB invocation in this harness must be a synthetic read.
        assert method == "GET" and path.startswith("content_jobs?select=")
        assert not kwargs
        calls["db"].append(path)
        return [dict(FAKE_ROW)]

    def forbidden_worker(name):
        async def worker():
            calls["workers"].append(name)
            raise AssertionError(f"worker started: {name}")
        return worker

    for name in (
        "content_worker_loop", "content_router_loop", "content_asset_worker_loop",
        "audio_worker_loop", "final_render_worker_loop", "publishing_worker_loop",
    ):
        monkeypatch.setattr(main, name, forbidden_worker(name))

    def forbidden_network(*args, **kwargs):
        raise AssertionError("external network attempted by security harness")

    def forbidden_video(*args, **kwargs):
        raise AssertionError("video storage or signing touched by unauthorized request")

    monkeypatch.setattr(urllib.request, "urlopen", fake_auth)
    monkeypatch.setattr(socket.socket, "connect", forbidden_network)
    monkeypatch.setattr(content_jobs_api, "_supabase_request", fake_db)
    monkeypatch.setattr(main, "create_signed_video_url", forbidden_video)
    assert not main._embedded_workers_enabled()

    with TestClient(main.app) as client:
        yield client, calls
    assert calls["workers"] == []


def _bootstrap(client, bearer):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    return client.post("/auth/soloforge/bootstrap", headers=headers)


def _app_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_owner_allow_and_private_read_only_endpoint(isolated_api):
    client, calls = isolated_api
    response = _bootstrap(client, "owner-supabase")
    assert response.status_code == 200
    body = response.json()
    assert body["identity_provider"] == "supabase_github"
    assert body["session_token"].startswith(f"v2.{OWNER}.")
    assert 0 < body["expires_at"] - int(time.time()) <= 900
    assert client.get(
        "/auth/soloforge/status", headers=_app_headers(body["session_token"])
    ).json()["authenticated"] is True
    queue = client.get("/v1/content-jobs?limit=1", headers=_app_headers(body["session_token"]))
    assert queue.status_code == 200
    assert queue.json() == {"items": [FAKE_ROW]}
    assert len(calls["db"]) == 1


@pytest.mark.parametrize("bearer", (
    "anonymous-supabase", "nonowner-supabase", "owner-wrong-provider", "invalid"
))
def test_untrusted_supabase_identities_are_denied(isolated_api, bearer):
    client, calls = isolated_api
    assert _bootstrap(client, bearer).status_code == 403
    assert calls["db"] == []


def test_missing_bearer_and_legacy_exchange_denied(isolated_api):
    client, calls = isolated_api
    assert _bootstrap(client, None).status_code == 401
    assert client.post(
        "/auth/soloforge/exchange", headers=_app_headers("legacy-provider")
    ).status_code == 410
    assert calls["auth"] == []


def test_private_route_and_video_denied_before_data_or_storage(isolated_api):
    client, calls = isolated_api
    for headers in ({}, _app_headers("forged-app-token")):
        assert client.get("/v1/content-jobs?limit=1", headers=headers).status_code == 401
        assert client.get("/v1/content-video/fixture-only-job", headers=headers).status_code == 401
    assert calls["db"] == []


def test_expired_and_legacy_app_sessions_denied(isolated_api):
    client, calls = isolated_api
    now = int(time.time())
    expired = f"v2.{OWNER}.{now - 901}.{now - 1}.fixture-nonce"
    expired = f"{expired}.{auth._sign(expired)}"
    legacy = f"v1.{now + 900}.fixture-nonce"
    legacy = f"{legacy}.{auth._sign(legacy)}"
    for token in (expired, legacy):
        headers = _app_headers(token)
        assert client.get("/auth/soloforge/status", headers=headers).json()["authenticated"] is False
        assert client.get("/v1/content-jobs?limit=1", headers=headers).status_code == 401
        assert client.get("/v1/content-video/fixture-only-job", headers=headers).status_code == 401
    assert calls["db"] == []


def test_fresh_owner_session_requires_owner_supabase_bearer(isolated_api):
    client, calls = isolated_api
    first = _bootstrap(client, "owner-supabase").json()["session_token"]
    second = client.post(
        "/auth/soloforge/refresh", headers=_app_headers("owner-supabase")
    )
    assert second.status_code == 200
    assert second.json()["session_token"] != first
    assert client.post(
        "/auth/soloforge/refresh", headers=_app_headers(first)
    ).status_code == 403
    assert client.post(
        "/auth/soloforge/refresh", headers=_app_headers("nonowner-supabase")
    ).status_code == 403
    assert calls["db"] == []
