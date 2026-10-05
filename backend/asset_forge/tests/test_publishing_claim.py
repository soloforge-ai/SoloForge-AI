"""Isolated publishing claim regressions; no production DB/provider calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, Lock
from urllib.parse import parse_qs
import urllib.request

import pytest
from fastapi import HTTPException

from backend import publishing_api as api


@pytest.fixture
def publishing(monkeypatch):
    row = {"id": "job-claim-test", "status": "READY_TO_PUBLISH",
           "publish_status": "PENDING", "publora_post_id": None,
           "content_package": {"pipeline_route": "TEXT"}}
    lock = Lock()
    state = {"row": row, "submissions": [], "writes": [],
             "claim_failure": False, "finish_failure": False}
    scheduled = datetime.now(timezone.utc) + timedelta(minutes=5)

    def forbidden_network(*args, **kwargs):
        raise AssertionError("External network is forbidden in publishing tests")

    def db(method, path, body=None, prefer=None):
        with lock:
            if method == "GET":
                return [deepcopy(row)]
            assert method == "PATCH"
            assert prefer == "return=representation"
            filters = parse_qs(path.split("?", 1)[1])
            assert filters["id"] == ["eq.job-claim-test"]
            assert filters["publora_post_id"] == ["is.null"]
            expected = filters["status"][0].removeprefix("eq.")
            if expected == "READY_TO_PUBLISH" and state["claim_failure"]:
                raise RuntimeError("Claim response unavailable")
            if expected == "PUBLISHING" and state["finish_failure"]:
                raise RuntimeError("Finish response unavailable")
            if row["status"] != expected or row["publora_post_id"] is not None:
                return []
            state["writes"].append(deepcopy(body))
            row.update(deepcopy(body))
            return [deepcopy(row)]

    def submit(job, **kwargs):
        assert job["status"] == "PUBLISHING"
        assert row["status"] == "PUBLISHING"
        assert job["content_package"]["scheduled_time"] == scheduled.isoformat()
        state["submissions"].append(deepcopy(job))
        failure = state.get("provider_failure")
        if failure:
            raise failure
        return state.get("provider_payload", {"postGroupId": "remote-group-test"})

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    monkeypatch.setattr(api, "_supabase_request", db)
    monkeypatch.setattr(api, "list_connections", lambda: [])
    monkeypatch.setattr(api, "submit_to_publora", submit)
    monkeypatch.setattr(api, "_require_session", lambda _: None)
    monkeypatch.setattr(api, "publish_now_time", lambda: scheduled)
    return state, scheduled


def test_success_claims_before_submit_and_duplicate_is_rejected(publishing):
    state, scheduled = publishing
    result = api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert result["publish_status"] == "QUEUED"
    assert result["publora_post_id"] == "remote-group-test"
    with pytest.raises(HTTPException) as exc:
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert exc.value.status_code == 409
    assert len(state["submissions"]) == 1
    assert [w["status"] for w in state["writes"]] == ["PUBLISHING", "PUBLISHING"]


def test_concurrent_publish_now_and_schedule_submit_once(monkeypatch, publishing):
    state, scheduled = publishing
    barrier, lock = Barrier(2), Lock()
    provider_entered, release = Event(), Event()
    original_get, original_submit = api._get_job, api.submit_to_publora

    def simultaneous_read(job_id):
        snapshot = original_get(job_id)
        barrier.wait(timeout=5)
        return snapshot

    def slow_provider(job, **kwargs):
        provider_entered.set()
        assert release.wait(timeout=5)
        return original_submit(job, **kwargs)

    monkeypatch.setattr(api, "_get_job", simultaneous_read)
    monkeypatch.setattr(api, "submit_to_publora", slow_provider)
    outcomes = []

    def request(schedule):
        try:
            if schedule:
                result = api.schedule("job-claim-test",
                    api.ScheduleRequest(platform_ids=["facebook-test"],
                                        scheduled_time=scheduled), "owner-fixture")
            else:
                result = api.publish_now("job-claim-test",
                    api.PublishRequest(platform_ids=["facebook-test"]), "owner-fixture")
            outcome = ("ok", result)
        except HTTPException as exc:
            outcome = ("error", exc.status_code)
            release.set()
        with lock:
            outcomes.append(outcome)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(request, value) for value in (False, True)]
        try:
            assert provider_entered.wait(timeout=5)
            for future in futures:
                future.result(timeout=10)
        finally:
            release.set()
    assert sorted(item[0] for item in outcomes) == ["error", "ok"]
    assert ("error", 409) in outcomes
    assert len(state["submissions"]) == 1


@pytest.mark.parametrize("failure", [
    RuntimeError("Publora is unavailable"), TimeoutError("ambiguous timeout"),
    ValueError("provider validation failed")])
def test_provider_failure_keeps_claim_and_blocks_retry(publishing, failure):
    state, scheduled = publishing
    state["provider_failure"] = failure
    with pytest.raises((HTTPException, TimeoutError)):
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert state["row"]["status"] == "PUBLISHING"
    assert state["row"]["publora_post_id"] is None
    assert state["row"]["content_package"]["publish_platform_ids"] == ["facebook-test"]
    assert state["row"]["content_package"]["scheduled_time"] == scheduled.isoformat()
    with pytest.raises(HTTPException) as exc:
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert exc.value.status_code == 409
    assert len(state["submissions"]) == 1


@pytest.mark.parametrize("mode", ["missing_id", "finish_failure"])
def test_ambiguous_completion_keeps_claim_without_resubmit(publishing, mode):
    state, scheduled = publishing
    if mode == "missing_id":
        state["provider_payload"] = {}
    else:
        state["finish_failure"] = True
    with pytest.raises((HTTPException, RuntimeError)):
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert state["row"]["status"] == "PUBLISHING"
    with pytest.raises(HTTPException) as exc:
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert exc.value.status_code == 409
    assert len(state["submissions"]) == 1


def test_claim_failure_never_calls_provider(publishing):
    state, scheduled = publishing
    state["claim_failure"] = True
    with pytest.raises(HTTPException) as exc:
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert exc.value.status_code == 502
    assert state["submissions"] == []


def test_existing_remote_reference_cannot_be_submitted_again(publishing):
    state, scheduled = publishing
    state["row"]["publora_post_id"] = "existing-remote-reference"
    with pytest.raises(HTTPException) as exc:
        api._submit("job-claim-test", ["facebook-test"], scheduled)
    assert exc.value.status_code == 409
    assert state["submissions"] == []
