"""MVP regression tests: Publora cannot dispatch through API or direct adapter."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from backend import publishing_policy
from backend import publishing_api
from backend import publora_publishing
from backend import performance_ingestion
from backend import soloforge_session


def test_publishing_gate_is_not_unlocked_by_env(monkeypatch):
    monkeypatch.setenv("PUBLORA_API_KEY", "fake-test-only")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "true")
    with pytest.raises(HTTPException) as error:
        publishing_policy.require_publishing_enabled()
    assert error.value.status_code == 503


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_direct_publora_adapter_fails_before_network(monkeypatch, method):
    network = Mock(side_effect=AssertionError("Publora must not be called"))
    monkeypatch.setattr(publora_publishing.urllib.request, "urlopen", network)
    monkeypatch.setenv("PUBLORA_API_KEY", "fake-test-only")
    with pytest.raises(HTTPException) as error:
        publora_publishing._publora_request(method, "/platform-connections")
    assert error.value.status_code == 503
    network.assert_not_called()


def test_publish_submission_fails_before_database(monkeypatch):
    database = Mock(side_effect=AssertionError("Publishing must not mutate jobs"))
    monkeypatch.setattr(publishing_api, "_supabase_request", database)
    with pytest.raises(HTTPException) as error:
        publishing_api._submit("job", [], publishing_api.publish_now_time())
    assert error.value.status_code == 503
    database.assert_not_called()


def test_publora_sync_worker_fails_before_database(monkeypatch):
    database = Mock(side_effect=AssertionError("Disabled sync must not read jobs"))
    monkeypatch.setattr(publora_publishing, "_supabase_request", database)
    with pytest.raises(HTTPException) as error:
        publora_publishing.sync_publishing_once()
    assert error.value.status_code == 503
    database.assert_not_called()


@pytest.mark.parametrize("action", ["publish-now", "schedule"])
def test_publishing_routes_do_not_dispatch(monkeypatch, action):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(publishing_api.router)
    monkeypatch.setattr(publishing_api, "_require_session", lambda _: None)
    database = Mock(side_effect=AssertionError("Disabled publish must not access DB"))
    monkeypatch.setattr(publishing_api, "_supabase_request", database)
    payload = {"platform_ids": []}
    if action == "schedule":
        payload["scheduled_time"] = "2027-01-01T12:00:00Z"
    response = TestClient(app).post(f"/v1/publishing/job-1/{action}", json=payload)
    assert response.status_code == 503
    database.assert_not_called()


@pytest.mark.parametrize("entry", [
    "request", "get_post", "list_connections", "submit_to_publora", "sync",
    "provider_capabilities", "sync_metadata",
])
def test_all_publora_entry_points_deny_before_side_effects(monkeypatch, entry):
    """Use real policy/adapter calls, including retained metadata integrations."""
    database = Mock(side_effect=AssertionError("Disabled Publora must not access DB"))
    network = Mock(side_effect=AssertionError("Disabled Publora must not use network"))
    monkeypatch.setattr(publora_publishing, "_supabase_request", database)
    monkeypatch.setattr(performance_ingestion, "_supabase_request", database)
    monkeypatch.setattr(publora_publishing.urllib.request, "urlopen", network)
    scheduled = datetime.now(timezone.utc) + timedelta(days=1)
    calls = {
        "request": lambda: publora_publishing._publora_request("POST", "/create-post"),
        "get_post": lambda: publora_publishing.get_post("fixture-post"),
        "list_connections": publora_publishing.list_connections,
        "submit_to_publora": lambda: publora_publishing.submit_to_publora(
            {"id": "fixture-job", "caption": "Fixture",
             "content_package": {"asset_storage_path": "fixture/image.png"}},
            platform_ids=["facebook-fixture"], scheduled_time=scheduled,
        ),
        "sync": publora_publishing.sync_publishing_once,
        "provider_capabilities": performance_ingestion.provider_capabilities,
        "sync_metadata": lambda: performance_ingestion.sync_publora_metadata(
            {"id": "fixture-job", "publora_post_id": "fixture-post"},
        ),
    }
    with pytest.raises(HTTPException) as error:
        calls[entry]()
    assert error.value.status_code == 503
    database.assert_not_called()
    network.assert_not_called()


@pytest.mark.parametrize("action", ["connections", "publish-now", "schedule"])
@pytest.mark.parametrize("identity", ["missing", "forged", "expired", "nonowner", "owner"])
def test_publishing_security_integration_keeps_auth_and_policy_closed(
    monkeypatch, action, identity,
):
    """Real owner-session validation; no authentication or policy substitution."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    owner = "00000000-0000-4000-8000-000000000010"
    other = "00000000-0000-4000-8000-000000000011"
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", owner)
    monkeypatch.setenv("SOLOFORGE_SESSION_SECRET", "fixture-only-publishing-secret-0123456789")
    monkeypatch.delenv("SOLOFORGE_SESSION_NOT_BEFORE", raising=False)
    if identity == "owner":
        token = soloforge_session.issue_session(owner).session_id
    elif identity in {"expired", "nonowner"}:
        now = int(time.time())
        user = other if identity == "nonowner" else owner
        issued, expiry = (now - 901, now - 1) if identity == "expired" else (now, now + 900)
        payload = f"v2.{user}.{issued}.{expiry}.fixture-nonce"
        token = f"{payload}.{soloforge_session._sign(payload)}"
    else:
        token = "forged-fixture-token" if identity == "forged" else None

    database = Mock(side_effect=AssertionError("Denied route must not access DB"))
    network = Mock(side_effect=AssertionError("Denied route must not use network"))
    monkeypatch.setattr(publishing_api, "_supabase_request", database)
    monkeypatch.setattr(publora_publishing, "_supabase_request", database)
    monkeypatch.setattr(publora_publishing.urllib.request, "urlopen", network)
    app = FastAPI()
    app.include_router(publishing_api.router)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with TestClient(app) as client:
        if action == "connections":
            response = client.get("/v1/publishing/connections", headers=headers)
        else:
            body = {"platform_ids": ["facebook-fixture"]}
            if action == "schedule":
                body["scheduled_time"] = "2027-01-01T12:00:00Z"
            response = client.post(
                f"/v1/publishing/fixture-job/{action}", headers=headers, json=body,
            )
    assert response.status_code == (503 if identity == "owner" else 401)
    database.assert_not_called()
    network.assert_not_called()
