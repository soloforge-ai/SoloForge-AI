"""Offline member authority and durable spending protocol verification."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import threading
import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from backend import byop_ledger as spend, byop_principal as identity


PRINCIPALS = ["owner:11111111-1111-4111-8111-111111111111",
              "member:22222222-2222-4222-8222-222222222222",
              "member:33333333-3333-4333-8333-333333333333"]
SNAPSHOT = {"credential_id": "credential-1", "job_id": "job-1", "revision": 1,
            "operation": "ceo_image", "model": "offline-fixture", "image_count": 1,
            "prompt_sha256": "a" * 64, "reference_sha256": "b" * 64, "settings": {}}


@pytest.fixture(scope="module")
def pg(tmp_path_factory):
    from test_owner_v2 import Database
    root = Path(__file__).resolve().parents[1]
    schema = tmp_path_factory.mktemp("byop") / "schema.sql"
    schema.write_text("create schema auth; create table auth.users(id uuid primary key);\n"
                      + (root / "sql/byop_v1_candidate.sql").read_text())
    process = subprocess.Popen(["node", str(root / "tests/owner_v2_pg_bridge.mjs"), str(schema)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    assert json.loads(process.stdout.readline()) == {"ready": True}
    db = Database(process)
    yield db
    process.stdin.close()
    assert process.wait(timeout=15) == 0


class Store:
    def __init__(self, db):
        self.db = db

    def read(self, principal):
        row = self.db.query("select revision,state from public.byop_ledgers where principal=$1",
                            [principal], "service_role")[0]
        return row["revision"], row["state"]

    def cas(self, principal, revision, state):
        return self.db.query("select public.byop_ledger_cas($1,$2,$3) as ok",
                             [principal, revision, json.dumps(state)], "service_role")[0]["ok"]


@pytest.fixture
def ledger(pg):
    pg.query("truncate public.byop_ledgers")
    for p in PRINCIPALS:
        pg.query("insert into public.byop_ledgers(principal,state) values($1,$2)",
                 [p, json.dumps({"budget": 100, "settled": 0, "concurrency_limit": 1})])
    return spend.Ledger(Store(pg), lambda _: {"basis": "OFFLINE FIXTURE ONLY",
                        "maximum_micro_pollen": 70, "expires_at": 1200}, lambda: 1000)


def consent(ledger, principal, snapshot=None):
    return ledger.consent(principal, snapshot or SNAPSHOT, 80, 1100)["consent_id"]


@pytest.mark.parametrize("principal", PRINCIPALS)
def test_exact_consent_reservation_and_started_replay_denial(ledger, principal):
    c = consent(ledger, principal)
    eid = str(uuid4())
    first = ledger.reserve(principal, c, eid)
    assert ledger.reserve(principal, c, eid) == first
    assert ledger.start(principal, eid, SNAPSHOT)["state"] == "CALL_STARTED"
    with pytest.raises(HTTPException):
        ledger.start(principal, eid, SNAPSHOT)
    assert ledger.outcome(principal, eid)["state"] == "UNKNOWN"
    with pytest.raises(HTTPException):
        ledger.start(principal, eid, SNAPSHOT)


def test_foreign_consent_and_execution_are_inaccessible(ledger):
    c = consent(ledger, PRINCIPALS[0])
    eid = str(uuid4())
    ledger.reserve(PRINCIPALS[0], c, eid)
    for foreign in PRINCIPALS[1:]:
        with pytest.raises(HTTPException):
            ledger.reserve(foreign, c, str(uuid4()))
        with pytest.raises(HTTPException):
            ledger.start(foreign, eid, SNAPSHOT)


def test_concurrent_reservations_have_one_winner(ledger):
    p = PRINCIPALS[1]
    consents = [consent(ledger, p), consent(ledger, p)]
    def attempt(c):
        try:
            ledger.reserve(p, c, str(uuid4()))
            return True
        except HTTPException:
            return False
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(attempt, consents)) == 1


def test_insufficient_budget(ledger, pg):
    p = PRINCIPALS[0]
    pg.query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','10') where principal=$1", [p])
    c = consent(ledger, p)
    with pytest.raises(HTTPException) as error:
        ledger.reserve(p, c, str(uuid4()))
    assert error.value.detail == "Principal budget exhausted"


def test_crash_restart_retains_call_started_and_reservation(ledger):
    p = PRINCIPALS[0]
    c = consent(ledger, p)
    eid = str(uuid4())
    ledger.reserve(p, c, eid)
    ledger.start(p, eid, SNAPSHOT)
    restarted = spend.Ledger(ledger.store, ledger.pricing, ledger.clock)
    assert restarted.reserve(p, c, eid)["state"] == "CALL_STARTED"
    with pytest.raises(HTTPException):
        restarted.start(p, eid, SNAPSHOT)
    with pytest.raises(HTTPException):
        restarted.reserve(p, consent(restarted, p), str(uuid4()))


def test_successful_image_does_not_settle_unknown_charge(ledger):
    p = PRINCIPALS[2]
    c = consent(ledger, p)
    eid = str(uuid4())
    ledger.reserve(p, c, eid)
    ledger.start(p, eid, SNAPSHOT)
    result = ledger.outcome(p, eid, generated=True, asset={"sha256": "c" * 64})
    assert result["state"] == "GENERATED" and result["reserved"] == 70
    with pytest.raises(HTTPException):
        ledger.reserve(p, consent(ledger, p), str(uuid4()))


def test_expired_consent_and_changed_snapshot(ledger):
    p = PRINCIPALS[0]
    c = consent(ledger, p)
    eid = str(uuid4())
    ledger.reserve(p, c, eid)
    with pytest.raises(HTTPException):
        ledger.start(p, eid, {**SNAPSHOT, "model": "changed"})
    ledger.clock = lambda: 1300
    with pytest.raises(HTTPException):
        ledger.start(p, eid, SNAPSHOT)


def test_pricing_unavailable_fails_closed(ledger):
    ledger.pricing = spend.unavailable_pricing
    with pytest.raises(HTTPException) as e:
        consent(ledger, PRINCIPALS[0])
    assert e.value.status_code == 503


@pytest.mark.parametrize("mutation", ["snapshot", "reserved", "principal", "consent_id"])
def test_sql_rejects_snapshot_or_reservation_mutation(ledger, mutation):
    p = PRINCIPALS[0]
    eid = str(uuid4())
    ledger.reserve(p, consent(ledger, p), eid)
    revision, state = ledger.store.read(p)
    original = deepcopy(state)
    state["executions"][eid][mutation] = 71 if mutation == "reserved" else "tampered"
    with pytest.raises(RuntimeError, match="immutable|Invalid principal execution"):
        ledger.store.cas(p, revision, state)
    assert ledger.store.read(p) == (revision, original)


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_sql_denies_client_ledger_and_membership_access(pg, role):
    for table in ["byop_ledgers", "soloforge_memberships"]:
        with pytest.raises(RuntimeError, match="permission denied"):
            pg.query("select * from public." + table, role=role)
    with pytest.raises(RuntimeError, match="permission denied"):
        pg.query("select public.byop_ledger_cas('x',0,'{}')", role=role)


@pytest.mark.parametrize("status", ["PENDING", "SUSPENDED", "DISABLED", None])
def test_membership_is_rechecked_and_inactive_denied(monkeypatch, status):
    p = identity.Principal("member", PRINCIPALS[1].split(":")[1])
    monkeypatch.setattr(identity, "supabase_request", lambda *a: [] if status != "ACTIVE" else [{"user_id": p.id}])
    with pytest.raises(HTTPException) as e:
        identity.require_active(p)
    assert e.value.status_code == 403


def test_supabase_identity_requires_active_server_membership(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, *args):
            return json.dumps({"id": PRINCIPALS[1].split(":")[1], "is_anonymous": False,
                               "user_metadata": {"role": "owner", "status": "ACTIVE"}}).encode()
    monkeypatch.setenv("SUPABASE_URL", "https://offline.invalid")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "offline")
    monkeypatch.setattr(identity.urllib.request, "urlopen", lambda *a, **k: Response())
    monkeypatch.setattr(identity, "supabase_request", lambda *a: [])
    with pytest.raises(HTTPException):
        identity.authenticate("Bearer member-fake")
    monkeypatch.setattr(identity, "supabase_request", lambda *a: [{"user_id": "active"}])
    assert identity.authenticate("Bearer member-fake").kind == "member"


def test_invalid_owner_never_falls_back_to_member(monkeypatch):
    monkeypatch.setattr(identity.OwnerV2, "authenticate", lambda *a: (_ for _ in ()).throw(identity.Unauthorized()))
    monkeypatch.setattr(identity.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Owner fallback forbidden"))
    with pytest.raises(HTTPException) as e:
        identity.authenticate("Bearer sf_owner_v2_invalid")
    assert e.value.status_code == 401


@pytest.mark.parametrize("principal_key", PRINCIPALS)
def test_offline_connect_authorize_generate_review_render_disconnect(ledger, monkeypatch, principal_key):
    from backend.byop_flow import Flow
    from backend import pollinations_sk_lifecycle
    from io import BytesIO
    import base64
    import hashlib
    import zipfile
    import runtime
    forge = runtime.asset_forge_main
    principal = identity.Principal(*principal_key.split(":"))
    active = {principal.key: True}
    master = (Path(__file__).resolve().parents[3] / "frontend/assets/characters/ceo/references/master.png").read_bytes()
    credentials = {}
    jobs = {}
    calls = []

    def authenticate(auth):
        if auth != principal.key or not active.get(auth):
            raise HTTPException(403, "Inactive principal")
        return principal

    class Repository:
        def submit_pending(self, p, token):
            cid = str(uuid4())
            credentials[cid] = {"principal": p, "token": token, "expires_at": time.time() + 3600,
                                "verification_status": "PENDING_VERIFICATION",
                                "provider_ownership_verified": False}
            return {"credential_id": cid, "spending_authorized": False}
        def credential(self, p, cid):
            row = credentials.get(cid)
            return deepcopy(row) if row and row["principal"] == p else None
        def expected_subject(self, p): return "independently-verified-" + p
        def claim_execution(self, p, execution_id, snapshot, ledger):
            return ledger.start(p, execution_id, snapshot)
        def promote(self, p, cid, result):
            assert p == credentials[cid]["principal"]
            assert result["provider_subject"] == self.expected_subject(p)
            credentials[cid].update(result)
            return {k: v for k, v in result.items() if k != "token"}
        def create_content_job(self, p, request, script="SoloForge CEO."):
            jid = str(uuid4())
            jobs[jid] = {"id": jid, "principal": p, "revision": 1,
                         "model": "offline-fixture", "status": "ASSET_QUEUED",
                         "content_package": {"asset_forge_request": request,
                                             "ceo_identity_required": True, "pipeline_route": "VIDEO"}}
            return deepcopy(jobs[jid])
        def content_job(self, p, jid):
            row = jobs.get(jid)
            return deepcopy(row) if row and row["principal"] == p else None
        def store_content_asset(self, p, jid, revision, image, sha, branding):
            assert jobs[jid]["principal"] == p and jobs[jid]["revision"] == revision
            assert hashlib.sha256(image).hexdigest() == sha
            self.image = image
            package = jobs[jid]["content_package"]
            package.update(asset_sha256=sha, asset_storage_path=f"{jid}/{sha}.png",
                           asset_status="READY", asset_review_status="PENDING")
            jobs[jid]["status"] = "READY_FOR_REVIEW"
            return {"sha256": sha, "path": package["asset_storage_path"]}
        def review_content_asset(self, p, jid, revision, sha, approved):
            assert jobs[jid]["principal"] == p and jobs[jid]["revision"] == revision
            package = jobs[jid]["content_package"]
            assert package["asset_sha256"] == sha
            package.update(asset_review_status="APPROVED" if approved else "REJECTED",
                           asset_review_sha256=sha if approved else None)
            return deepcopy(jobs[jid])
        def finish_content_render(self, p, jid, revision, result):
            assert jobs[jid]["principal"] == p and jobs[jid]["revision"] == revision
            jobs[jid] = result
            return deepcopy(result)
        def claim_render(self, p, jid, revision):
            assert jobs[jid]["principal"] == p and jobs[jid]["revision"] == revision
            return deepcopy(jobs[jid])
        def disconnect(self, p, cid):
            if not self.credential(p, cid): return False
            credentials[cid]["disconnected"] = True
            return True

    repository = Repository()
    monkeypatch.setattr(forge, "_load_character_reference", lambda _: master)
    monkeypatch.setattr(pollinations_sk_lifecycle, "_userinfo", lambda _: (200, {"sub": repository.expected_subject(principal.key)}))
    def require_started():
        _, state = ledger.store.read(principal.key)
        assert any(e["state"] == "CALL_STARTED" for e in state["executions"].values())
    monkeypatch.setattr(forge, "require_generation_execution", require_started)
    def provider(prompt, reference, token):
        require_started()
        assert reference == master and token == "sk_offline_member"
        calls.append(token)
        return master
    monkeypatch.setattr(forge, "_generate_sheet", provider)
    def generate(snapshot, token):
        response = forge.build_asset_pack(forge.AssetForgeRequest.model_validate(snapshot["settings"]["request"]), access_token=token)
        assert response.generation_mode == "pollinations" and len(response.files) == 1
        with zipfile.ZipFile(BytesIO(base64.b64decode(response.zip_base64))) as archive:
            return archive.read(response.asset_pack_name + "/" + response.files[0])
    def render(job):
        # Provenance boundary fixture; real FFmpeg rendering is covered by #211.
        sha = hashlib.sha256(b"offline-render-fixture").hexdigest()
        package = job["content_package"]
        job.update(video_storage_path=f"{job['id']}/{sha}.mp4", video_url=None,
                   render_qa={"status": "PASS", "source_asset_sha256": package["asset_sha256"],
                              "source_asset_storage_path": package["asset_storage_path"],
                              "output_sha256": sha, "output_storage_path": f"{job['id']}/{sha}.mp4"})
        return job

    flow = Flow(authenticate, repository, ledger, generate, render)
    auth = principal.key
    cid = flow.connect(auth, "sk_offline_member")["credential_id"]
    jid = flow.create_job(auth, {"character": "CEO", "generation_layout": "single_character",
                               "quantity": 1, "pose_intent": "presenting", "expression": "calm"})["id"]
    with pytest.raises(HTTPException):
        flow.authorize(auth, cid, jid, 80, 1100)
    assert flow.verify(auth, cid)["verification_status"] == "VERIFIED"
    consent_id = flow.authorize(auth, cid, jid, 80, 1100)["consent_id"]
    eid = str(uuid4())
    flow.execute(auth, consent_id, eid)
    assert len(calls) == 1
    with pytest.raises(HTTPException):
        flow.execute(auth, consent_id, eid)
    flow.review(auth, jid, repository.image, False)
    with pytest.raises(ValueError):
        flow.render_job(auth, jid)
    flow.review(auth, jid, repository.image, True)
    assert flow.render_job(auth, jid)["render_qa"]["status"] == "PASS"
    from backend.publishing_policy import require_publishing_enabled
    with pytest.raises(HTTPException):
        require_publishing_enabled()
    assert flow.disconnect(auth, cid)["upstream_revocation_confirmed"] is False
    with pytest.raises(HTTPException):
        flow.authorize(auth, cid, jid, 80, 1100)
    active[auth] = False
    with pytest.raises(HTTPException):
        flow.review(auth, jid, repository.image, True)
