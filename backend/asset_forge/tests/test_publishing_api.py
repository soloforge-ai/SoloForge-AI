"""Publish claim regressions using isolated, stateful storage and Publora doubles."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier, Lock
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend import publishing_api as api


SCHEDULED = datetime.now(timezone.utc) + timedelta(days=1)
PLATFORMS = ["facebook-account"]


@pytest.fixture
def storage(monkeypatch):
    state = {
        "id": "job-1", "status": "READY_TO_PUBLISH",
        "publish_status": "PENDING", "publora_post_id": None,
        "caption": "Caption", "content_package": {"content_id": "C001"},
    }
    calls = []
    lock = Lock()

    def request(method, path, body=None, prefer=None):
        query = parse_qs(urlsplit(path).query)
        with lock:
            calls.append((method, query, deepcopy(body), prefer))
            if method == "GET":
                return [deepcopy(state)]
            assert method == "PATCH"
            assert query["id"] == ["eq.job-1"]
            assert query["publora_post_id"] == ["is.null"]
            assert prefer == "return=representation"
            if query["status"] != [f"eq.{state['status']}"] or state["publora_post_id"] is not None:
                return []
            state.update(deepcopy(body))
            return [deepcopy(state)]

    monkeypatch.setattr(api, "_supabase_request", request)
    monkeypatch.setattr(api, "list_connections", lambda: [])
    return state, calls


def test_success_claim_precedes_publora_and_saves_id(monkeypatch, storage):
    state, calls = storage

    def publish(job, **kwargs):
        assert state["status"] == job["status"] == "PUBLISHING"
        assert state["publish_status"] == "PENDING"
        assert state["publora_post_id"] is None
        assert state["content_package"] == {
            "content_id": "C001", "publish_platform_ids": PLATFORMS,
            "scheduled_time": SCHEDULED.isoformat(),
        }
        assert datetime.fromisoformat(state["updated_at"]).tzinfo is not None
        return {"postGroupId": "post-1"}

    submit = Mock(side_effect=publish)
    monkeypatch.setattr(api, "submit_to_publora", submit)
    result = api._submit("job-1", PLATFORMS, SCHEDULED)
    submit.assert_called_once()
    assert result["status"] == "PUBLISHING"
    assert result["publish_status"] == "QUEUED"
    assert result["publora_post_id"] == "post-1"
    assert result["error_message"] is None
    assert [call[0] for call in calls] == ["GET", "PATCH", "PATCH"]
    assert calls[1][1]["status"] == ["eq.READY_TO_PUBLISH"]
    assert calls[2][1]["status"] == ["eq.PUBLISHING"]


def test_lost_claim_returns_409_without_publora(monkeypatch, storage):
    state, _ = storage
    stale = deepcopy(state)
    state["status"] = "PUBLISHING"
    monkeypatch.setattr(api, "_get_job", lambda _: stale)
    submit = Mock()
    monkeypatch.setattr(api, "submit_to_publora", submit)
    with pytest.raises(HTTPException) as error:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert error.value.status_code == 409
    submit.assert_not_called()


def test_two_concurrent_stale_reads_only_one_submits(monkeypatch, storage):
    state, _ = storage
    stale = deepcopy(state)
    barrier = Barrier(2)

    def read(_):
        barrier.wait(timeout=5)
        return deepcopy(stale)

    monkeypatch.setattr(api, "_get_job", read)
    submit = Mock(return_value={"postGroupId": "post-1"})
    monkeypatch.setattr(api, "submit_to_publora", submit)

    def run():
        try:
            return api._submit("job-1", PLATFORMS, SCHEDULED)["publora_post_id"]
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results, key=str) == [409, "post-1"]
    submit.assert_called_once()
    assert state["status"] == "PUBLISHING"


@pytest.mark.parametrize("outcome", [
    RuntimeError("Publora is unavailable"), {}, {"postGroupId": " "},
    {"postGroupId": 123}, {"postGroupId": {"unexpected": "value"}},
])
def test_ambiguous_result_keeps_claim_and_blocks_next_request(monkeypatch, storage, outcome):
    state, calls = storage
    submit = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    monkeypatch.setattr(api, "submit_to_publora", submit)
    with pytest.raises(HTTPException) as error:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert error.value.status_code == 502
    assert state["status"] == "PUBLISHING"
    assert state["publish_status"] == "PENDING"
    assert state["publora_post_id"] is None
    assert len([call for call in calls if call[0] == "PATCH"]) == 1
    with pytest.raises(HTTPException) as duplicate:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert duplicate.value.status_code == 409
    submit.assert_called_once()


def test_storage_failure_after_publora_does_not_resubmit(monkeypatch, storage):
    state, _ = storage
    original = api._supabase_request

    def request(method, path, **kwargs):
        if method == "PATCH" and kwargs["body"].get("publora_post_id"):
            raise RuntimeError("SoloForge storage is unavailable")
        return original(method, path, **kwargs)

    monkeypatch.setattr(api, "_supabase_request", request)
    submit = Mock(return_value={"postGroupId": "post-1"})
    monkeypatch.setattr(api, "submit_to_publora", submit)
    with pytest.raises(HTTPException) as error:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert error.value.status_code == 502
    assert (state["status"], state["publish_status"], state["publora_post_id"]) == (
        "PUBLISHING", "PENDING", None,
    )
    with pytest.raises(HTTPException) as duplicate:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert duplicate.value.status_code == 409
    submit.assert_called_once()


@pytest.mark.parametrize("action", ["publish-now", "schedule"])
def test_routes_return_409_for_lost_claim(monkeypatch, storage, action):
    state, _ = storage
    stale = deepcopy(state)
    state["status"] = "PUBLISHING"
    monkeypatch.setattr(api, "_get_job", lambda _: stale)
    monkeypatch.setattr(api, "_require_session", lambda _: None)
    submit = Mock()
    monkeypatch.setattr(api, "submit_to_publora", submit)
    app = FastAPI()
    app.include_router(api.router)
    body = {"platform_ids": PLATFORMS}
    if action == "schedule":
        body["scheduled_time"] = SCHEDULED.isoformat()
    with TestClient(app) as client:
        response = client.post(f"/v1/publishing/job-1/{action}", json=body)
    assert response.status_code == 409
    submit.assert_not_called()


def test_ready_job_with_existing_post_id_cannot_be_claimed(monkeypatch, storage):
    state, _ = storage
    state["publora_post_id"] = "existing-post"
    submit = Mock()
    monkeypatch.setattr(api, "submit_to_publora", submit)
    with pytest.raises(HTTPException) as error:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert error.value.status_code == 409
    assert state["publora_post_id"] == "existing-post"
    submit.assert_not_called()


def test_claim_response_timeout_never_calls_publora(monkeypatch, storage):
    state, _ = storage
    original = api._supabase_request

    def request(method, path, **kwargs):
        result = original(method, path, **kwargs)
        if method == "PATCH":
            raise RuntimeError("SoloForge storage is unavailable")
        return result

    monkeypatch.setattr(api, "_supabase_request", request)
    submit = Mock()
    monkeypatch.setattr(api, "submit_to_publora", submit)
    with pytest.raises(HTTPException) as error:
        api._submit("job-1", PLATFORMS, SCHEDULED)
    assert error.value.status_code == 502
    assert (state["status"], state["publish_status"], state["publora_post_id"]) == (
        "PUBLISHING", "PENDING", None,
    )
    submit.assert_not_called()
