"""Fail-closed counter tests: the original notification remains authoritative."""
from types import SimpleNamespace

from backend.ci_progress import confirmed_progress


def sample():
    event = SimpleNamespace(category="CI", event_type="ci.passed", commit_sha="abc", details={"job_id": 2, "run_id": 9})
    run = {"status": "completed", "head_sha": "abc", "run_attempt": 1}
    jobs = {"total_count": 2, "jobs": [
        {"id": 1, "status": "completed", "completed_at": "2026-01-01T00:00:01Z", "run_attempt": 1},
        {"id": 2, "status": "completed", "completed_at": "2026-01-01T00:00:02Z", "run_attempt": 1},
    ]}
    return event, run, jobs


def lookup(run, jobs):
    return lambda path: run if path.endswith("/runs/9") else jobs


def test_complete_multi_job():
    event, run, jobs = sample()
    assert confirmed_progress(event, fetch=lookup(run, jobs)) == (2, 2)


def test_failure_never_calls_api():
    event, _, _ = sample()
    event.event_type = "ci.failed"
    assert confirmed_progress(event, fetch=lambda _: 1 / 0) is None


def test_incomplete_run_falls_back():
    event, run, jobs = sample()
    run["status"] = "in_progress"
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_partial_job_list_falls_back():
    event, run, jobs = sample()
    jobs["total_count"] = 3
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_pending_job_falls_back():
    event, run, jobs = sample()
    jobs["jobs"][0]["status"] = "queued"
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_sha_mismatch_falls_back():
    event, run, jobs = sample()
    run["head_sha"] = "wrong"
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_attempt_mismatch_falls_back():
    event, run, jobs = sample()
    jobs["jobs"][0]["run_attempt"] = 2
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_single_job_has_no_counter():
    event, run, jobs = sample()
    jobs["jobs"] = jobs["jobs"][:1]
    jobs["total_count"] = 1
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_api_timeout_falls_back():
    event, _, _ = sample()
    def timeout(_):
        raise TimeoutError()
    assert confirmed_progress(event, fetch=timeout) is None


def test_unknown_job_falls_back():
    event, run, jobs = sample()
    event.details["job_id"] = 99
    assert confirmed_progress(event, fetch=lookup(run, jobs)) is None


def test_smoke_does_not_call_api():
    event, _, _ = sample()
    event.category = "SMK"
    assert confirmed_progress(event, fetch=lambda _: 1 / 0) is None


def test_missing_run_id_does_not_call_api():
    event, _, _ = sample()
    event.details["run_id"] = None
    assert confirmed_progress(event, fetch=lambda _: 1 / 0) is None
