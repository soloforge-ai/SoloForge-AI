from backend.ops_events import format_telegram_message, normalize_github_event


REPO = {"full_name": "soloforge-ai/SoloForge-AI"}


def _job_payload(*, conclusion, runner_name="", steps=None, name="production-smoke"):
    return {
        "action": "completed",
        "repository": REPO,
        "workflow_job": {
            "id": 77,
            "run_id": 88,
            "name": name,
            "workflow_name": "Asset Forge Production Smoke",
            "head_sha": "55467d2d7d03220dba292bfcb22836f8099f7d39",
            "conclusion": conclusion,
            "runner_name": runner_name,
            "steps": steps or [],
        },
    }


def test_runner_unavailable_is_infra_not_smoke_failure():
    event = normalize_github_event(
        "workflow_job",
        "delivery-1",
        _job_payload(conclusion="cancelled"),
    )
    assert event is not None
    assert event.event_type == "runner.unavailable"
    assert event.category == "CI"
    assert event.status == "INFRA"
    assert "Production Status: UNKNOWN" in format_telegram_message(event, 1)


def test_cancelled_after_runner_started_is_not_runner_unavailable():
    event = normalize_github_event(
        "workflow_job",
        "delivery-2",
        _job_payload(conclusion="cancelled", runner_name="GitHub Actions 42"),
    )
    assert event is not None
    assert event.event_type == "workflow.cancelled"
    assert event.status == "CANCELLED"


def test_smoke_success_and_failure_are_distinct():
    passed = normalize_github_event(
        "workflow_job", "delivery-3", _job_payload(conclusion="success")
    )
    failed = normalize_github_event(
        "workflow_job",
        "delivery-4",
        _job_payload(
            conclusion="failure",
            runner_name="GitHub Actions 42",
            steps=[{"name": "Wait for production health", "status": "completed"}],
        ),
    )
    assert passed is not None and passed.event_type == "production_smoke.passed"
    assert failed is not None and failed.event_type == "production_smoke.failed"
    assert failed.category == "SMK"


def test_other_repo_is_ignored():
    payload = _job_payload(conclusion="failure")
    payload["repository"] = {"full_name": "someone/else"}
    assert normalize_github_event("workflow_job", "delivery-5", payload) is None


def test_pull_request_merged():
    event = normalize_github_event(
        "pull_request",
        "delivery-6",
        {
            "action": "closed",
            "repository": REPO,
            "number": 136,
            "pull_request": {
                "number": 136,
                "title": "fix publishing",
                "merged": True,
                "merge_commit_sha": "abc123",
                "html_url": "https://example.test/pr/136",
            },
        },
    )
    assert event is not None
    assert event.event_type == "pull_request.merged"
    assert event.category == "GIT"



def test_duplicate_smoke_runs_share_logical_event_key():
    first = _job_payload(
        conclusion="success",
        runner_name="GitHub Actions 1",
        steps=[{"name": "Wait for production health", "status": "completed"}],
    )
    second = _job_payload(
        conclusion="success",
        runner_name="GitHub Actions 2",
        steps=[{"name": "Wait for production health", "status": "completed"}],
    )
    second["workflow_job"]["id"] = 78
    second["workflow_job"]["run_id"] = 89

    event_a = normalize_github_event("workflow_job", "delivery-a", first)
    event_b = normalize_github_event("workflow_job", "delivery-b", second)

    assert event_a is not None and event_b is not None
    assert event_a.event_key == event_b.event_key
    assert event_a.event_key == (
        "github:production_smoke:"
        "55467d2d7d03220dba292bfcb22836f8099f7d39:success"
    )


def test_smoke_failure_does_not_dedupe_with_success():
    passed = normalize_github_event(
        "workflow_job", "delivery-pass", _job_payload(conclusion="success")
    )
    failed = normalize_github_event(
        "workflow_job",
        "delivery-fail",
        _job_payload(
            conclusion="failure",
            runner_name="GitHub Actions 42",
            steps=[{"name": "Wait for production health", "status": "completed"}],
        ),
    )

    assert passed is not None and failed is not None
    assert passed.event_key != failed.event_key
