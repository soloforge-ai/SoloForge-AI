"""MVP regression tests: Publora cannot dispatch through API or direct adapter."""
from __future__ import annotations

from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from backend import publishing_policy
from backend import publishing_api
from backend import publora_publishing


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
