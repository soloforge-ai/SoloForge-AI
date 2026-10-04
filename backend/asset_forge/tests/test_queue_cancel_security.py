"""Queue cancellation security contract; no production secrets or I/O."""
from __future__ import annotations

from pathlib import Path

import pytest

from test_batch_a_security_integration import isolated_api, _bootstrap
from backend import content_jobs_api, publishing_api

JOB = "00000000-0000-4000-8000-000000000025"


def _owner(client):
    response = _bootstrap(client, "owner-supabase")
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['session_token']}"}


@pytest.mark.parametrize("bearer", (None, "anonymous-supabase", "nonowner-supabase", "invalid"))
def test_cancel_requires_owner_app_session(isolated_api, monkeypatch, bearer):
    client, calls = isolated_api
    def forbidden(*args, **kwargs):
        raise AssertionError("unauthorized cancellation reached database")
    monkeypatch.setattr(content_jobs_api, "_supabase_request", forbidden)
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    assert client.post(f"/v1/content-jobs/{JOB}/cancel", headers=headers).status_code == 403
    assert client.post("/v1/content-jobs/queue/reset", headers=headers).status_code == 403
    assert calls["workers"] == []


def test_owner_cancel_and_repeat_are_idempotent(isolated_api, monkeypatch):
    client, calls = isolated_api
    state = {"status": "READY_FOR_REVIEW", "events": ["BASELINE"],
             "asset": "preserved", "telegram": "preserved", "publora": None}
    def database(method, path, body=None, **kwargs):
        assert method == "POST" and path == "rpc/cancel_content_jobs"
        assert body == {"p_job_id": JOB}
        if state["status"] == "CANCELLED":
            return {"selected": 1, "eligible": 0, "cancelled": 0,
                    "already_cancelled": 1, "cancelled_ids": [], "skipped": []}
        state["status"] = "CANCELLED"
        state["events"].append("OWNER_CANCELLED")
        return {"selected": 1, "eligible": 1, "cancelled": 1,
                "already_cancelled": 0, "cancelled_ids": [JOB], "skipped": []}
    monkeypatch.setattr(content_jobs_api, "_supabase_request", database)
    headers = _owner(client)
    first = client.post(f"/v1/content-jobs/{JOB}/cancel", headers=headers)
    second = client.post(f"/v1/content-jobs/{JOB}/cancel", headers=headers)
    assert first.status_code == second.status_code == 200
    assert (first.json()["cancelled"], second.json()["cancelled"]) == (1, 0)
    assert state["events"] == ["BASELINE", "OWNER_CANCELLED"]
    assert state["asset"] == state["telegram"] == "preserved"
    assert calls["workers"] == []


def test_reset_reports_publishing_without_mutation(isolated_api, monkeypatch):
    client, calls = isolated_api
    ids = [JOB, "00000000-0000-4000-8000-000000000026"]
    requests = []
    def database(method, path, body=None, **kwargs):
        requests.append((method, path, body))
        assert method == "POST" and path == "rpc/cancel_content_jobs"
        assert body == {"p_job_id": None}
        return {"selected": 2, "eligible": 1, "cancelled": 1,
                "already_cancelled": 0, "cancelled_ids": [ids[0]],
                "skipped": [{"id": ids[1], "status": "PUBLISHING",
                             "reason": "EXTERNAL_RECONCILIATION_REQUIRED",
                             "publora_post_id": "draft-fixture"}]}
    monkeypatch.setattr(content_jobs_api, "_supabase_request", database)
    monkeypatch.setattr(content_jobs_api, "get_post", lambda post_id: {"status": "draft"})
    headers = _owner(client)
    assert client.post("/v1/content-jobs/queue/reset", headers=headers).status_code == 400
    response = client.post("/v1/content-jobs/queue/reset", headers=headers,
                           json={"confirmation": "CANCEL ALL ACTIVE JOBS"})
    assert response.status_code == 200
    assert response.json()["cancelled"] == 1
    assert response.json()["skipped"][0]["external_state"] == "draft"
    assert "publora_post_id" not in response.json()["skipped"][0]
    assert len(requests) == 1
    assert calls["workers"] == []


def test_publish_claim_precedes_external_submission(monkeypatch):
    calls = []
    job = {"id": JOB, "status": "READY_TO_PUBLISH", "content_package": {}}
    monkeypatch.setattr(publishing_api, "_get_job", lambda _: job)
    monkeypatch.setattr(publishing_api, "list_connections", lambda: [{"platformId": "facebook-fixture"}])
    monkeypatch.setattr(publishing_api, "default_platform_ids", lambda *_: ["facebook-fixture"])
    def database(method, path, **kwargs):
        calls.append("claim")
        assert "status=eq.READY_TO_PUBLISH" in path
        return []  # cancellation won the row race
    monkeypatch.setattr(publishing_api, "_supabase_request", database)
    monkeypatch.setattr(publishing_api, "submit_to_publora", lambda *_, **__: calls.append("PUBLISH"))
    with pytest.raises(Exception) as exc:
        publishing_api._submit(JOB, [], publishing_api.publish_now_time())
    assert getattr(exc.value, "status_code", None) == 409
    assert calls == ["claim"]


def test_migration_locks_rows_preserves_history_and_denies_revive():
    sql = Path("supabase/migrations/202610040001_content_queue_cancel.sql").read_text()
    assert "for update" in sql.lower()
    assert "old.status = 'CANCELLED'" in sql
    assert "insert into public.content_job_events" in sql
    assert "delete from" not in sql.lower()
    assert "EXTERNAL_RECONCILIATION_REQUIRED" in sql
    assert "grant execute on function public.cancel_content_jobs(uuid) to service_role" in sql
    assert "revoke all on function public.cancel_content_jobs(uuid) from public, anon, authenticated" in sql


def test_workers_and_retry_select_only_explicit_non_cancelled_states():
    worker_files = (
        "content_generation.py", "content_router.py", "content_asset_generation.py",
        "audio_generation.py", "final_render.py", "publora_publishing.py",
    )
    for name in worker_files:
        source = Path("backend/asset_forge/backend", name).read_text()
        assert "status=eq.CANCELLED" not in source
        assert "status=eq." in source, f"{name} must claim an explicit state"
    api = Path("backend/asset_forge/backend/content_jobs_api.py").read_text()
    assert '"CANCELLED"' not in api.partition("_REGENERATE_FROM = {")[2].partition("}")[0]


def test_no_external_mutation_in_cancellation_handler():
    source = Path("backend/asset_forge/backend/content_jobs_api.py").read_text()
    cancellation = source.partition("def _cancel_jobs(")[2].partition('@router.post("/queue/reset")')[0]
    assert '"rpc/cancel_content_jobs"' in cancellation
    assert "get_post(" in cancellation  # external state is read-only
    assert "submit_to_publora" not in cancellation
    assert "telegram" not in cancellation.lower()
