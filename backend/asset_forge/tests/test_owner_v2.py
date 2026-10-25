"""Real V2 SQL + backend + HTTP tests; only delivery/REST transport are replaced."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import threading
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.asset_forge.backend import owner_v2 as auth
from backend.asset_forge.backend import owner_v2_router as routes

ROOT = Path(__file__).resolve().parents[3]
OWNER = "11111111-1111-4111-8111-111111111111"
EMAIL = "owner@example.test"


class Database:
    def __init__(self, process):
        self.process = process
        self.lock = threading.Lock()
        self.calls = []

    def query(self, sql, params=(), role="postgres"):
        with self.lock:
            self.process.stdin.write(json.dumps({"sql": sql, "params": params, "role": role}) + "\n")
            self.process.stdin.flush()
            result = json.loads(self.process.stdout.readline())
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["rows"]

    def call(self, name, body):
        self.calls.append((name, body.copy()))
        args = ",".join(f"{key} => ${i}" for i, key in enumerate(body, 1))
        return self.query(f"select public.owner_v2_{name}({args}) as value", list(body.values()), "service_role")[0]["value"]


@pytest.fixture(scope="session")
def database():
    module = os.environ.get("OWNER_V2_TEST_PGLITE")
    if not module or not Path(module).is_file():
        pytest.fail("Set OWNER_V2_TEST_PGLITE to installed @electric-sql/pglite@0.3.14 dist/index.js")
    migration = ROOT / "supabase/migrations/20261024151629_owner_identity_v2.sql"
    github_bridge = ROOT / "supabase/migrations/20261025152000_owner_v2_github_bridge.sql"
    with subprocess.Popen(["node", str(Path(__file__).with_name("owner_v2_pg_bridge.mjs")), str(migration), str(github_bridge)],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1) as process:
        assert json.loads(process.stdout.readline()) == {"ready": True}
        yield Database(process)
        process.stdin.close()
        assert process.wait(timeout=15) == 0


class Mailbox:
    def __init__(self):
        self.messages = []
        self.fail = False

    def send(self, email, code):
        self.messages.append((email, code))
        if self.fail:
            raise auth.Unavailable("Owner V2 is unavailable")


@pytest.fixture
def setup(database, monkeypatch):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    database.query("truncate public.owner_v2_sessions, public.owner_v2_challenges, public.soloforge_owner_accounts, public.soloforge_owners")
    database.query("select public.owner_v2_bootstrap($1,$2)", [OWNER, EMAIL])
    database.calls.clear()
    mailbox = Mailbox()
    service = auth.OwnerV2(database.call, lambda: mailbox)
    monkeypatch.setattr(routes, "service", service)
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield database, mailbox, service, client


def proof(setup):
    db, mail, service, client = setup
    requested = client.post("/auth/owner-v2/request", json={"email": EMAIL})
    assert requested.status_code == 202
    assert requested.headers["cache-control"] == "no-store"
    data = requested.json()
    assert mail.messages[-1][0] == EMAIL
    assert mail.messages[-1][1] not in requested.text
    return {"challenge_id": data["challenge_id"], "browser_proof": data["browser_proof"], "code": mail.messages[-1][1]}


def login(setup):
    result = setup[3].post("/auth/owner-v2/verify", json=proof(setup))
    assert result.status_code == 200, result.text
    return result.json()["session_token"]


def test_full_passwordless_http_roundtrip_and_logout(setup):
    db, mail, service, client = setup
    token = login(setup)
    headers = {"Authorization": f"Bearer {token}"}
    identity = client.get("/auth/owner-v2/session", headers=headers)
    assert identity.status_code == 200
    assert identity.json() == {"owner_id": OWNER, "primary_email": EMAIL, "authenticated": True, "identity_version": "owner_v2"}
    assert client.post("/auth/owner-v2/logout", headers=headers).status_code == 204
    assert client.get("/auth/owner-v2/session", headers=headers).status_code == 401
    serialized = json.dumps(db.query("select * from public.owner_v2_sessions"))
    assert token not in serialized and auth.digest(token) in serialized


def test_no_seed_no_signup(setup):
    db, mail, service, client = setup
    db.query("truncate public.owner_v2_sessions,public.owner_v2_challenges,public.soloforge_owner_accounts,public.soloforge_owners")
    assert client.post("/auth/owner-v2/request", json={"email": EMAIL}).status_code == 202
    assert mail.messages == []
    assert db.query("select * from public.soloforge_owners") == []


def test_unknown_email_response_has_same_shape_and_no_delivery(setup):
    db, mail, service, client = setup
    r = client.post("/auth/owner-v2/request", json={"email": "other@example.test"})
    assert r.status_code == 202
    assert set(r.json()) == {"accepted", "challenge_id", "browser_proof", "expires_in"}
    assert not mail.messages and not db.query("select * from public.owner_v2_challenges")


def test_canonical_email_normalization(setup):
    db, mail, service, client = setup
    assert service.request("  OWNER@EXAMPLE.TEST  ")["accepted"]
    assert mail.messages[0][0] == EMAIL


@pytest.mark.parametrize("flag", [None, "", "false", "1", "yes"])
def test_disabled_fails_before_side_effects(setup, monkeypatch, flag):
    db, mail, service, client = setup
    monkeypatch.delenv("OWNER_V2_AUTH_ENABLED", raising=False)
    if flag is not None:
        monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", flag)
    r = client.post("/auth/owner-v2/request", json={"email": EMAIL})
    assert r.status_code == 503 and not db.calls and not mail.messages


@pytest.mark.parametrize("field", ["code", "browser_proof"])
def test_wrong_proof_and_attempt_cap(setup, field):
    db, mail, service, client = setup
    body = proof(setup)
    wrong = {**body, field: "A" * 43}
    for _ in range(5):
        assert client.post("/auth/owner-v2/verify", json=wrong).status_code == 401
    assert client.post("/auth/owner-v2/verify", json=body).status_code == 401
    assert db.query("select attempts from public.owner_v2_challenges")[0]["attempts"] == 5
    assert not db.query("select * from public.owner_v2_sessions")


def test_replay_and_parallel_redemption_issue_exactly_one_session(setup):
    db, mail, service, client = setup
    body = proof(setup)
    def redeem(_):
        try:
            return service.verify(**body)
        except auth.Unauthorized:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(redeem, range(8)))
    assert sum(r is not None for r in results) == 1
    assert len(db.query("select * from public.owner_v2_sessions")) == 1


def test_expired_code(setup):
    db, mail, service, client = setup
    body = proof(setup)
    db.query("update public.owner_v2_challenges set expires_at = clock_timestamp() - interval '1 second'")
    assert client.post("/auth/owner-v2/verify", json=body).status_code == 401


def test_expired_session(setup):
    db, mail, service, client = setup
    token = login(setup)
    db.query("update public.owner_v2_sessions set expires_at = clock_timestamp() - interval '1 second'")
    assert client.get("/auth/owner-v2/session", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_disable_reenable_revokes_old_sessions_and_challenges(setup):
    db, mail, service, client = setup
    token = login(setup)
    db.query("update public.owner_v2_challenges set created_at=clock_timestamp()-interval '61 seconds'")
    body = proof(setup)
    db.query("update public.soloforge_owners set status='disabled'")
    assert client.get("/auth/owner-v2/session", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    db.query("update public.soloforge_owners set status='active'")
    assert client.get("/auth/owner-v2/session", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/auth/owner-v2/verify", json=body).status_code == 401


def test_rate_limit_60_seconds_and_five_per_hour(setup):
    db, mail, service, client = setup
    service.request(EMAIL)
    service.request(EMAIL)
    assert len(mail.messages) == 1
    for _ in range(4):
        db.query("update public.owner_v2_challenges set created_at=created_at-interval '61 seconds'")
        service.request(EMAIL)
    assert len(mail.messages) == 5
    db.query("update public.owner_v2_challenges set created_at=created_at-interval '61 seconds'")
    service.request(EMAIL)
    assert len(mail.messages) == 5


def test_ambiguous_email_delivery_never_activates_or_retries(setup):
    db, mail, service, client = setup
    mail.fail = True
    assert client.post("/auth/owner-v2/request", json={"email": EMAIL}).status_code == 503
    assert len(mail.messages) == 1
    row = db.query("select * from public.owner_v2_challenges")[0]
    assert row["delivered_at"] is None
    assert all(name != "activate_challenge" for name, body in db.calls)
    assert db.call("consume_challenge", {"p_challenge_id": row["challenge_id"], "p_browser_hash": row["browser_hash"],
        "p_code_hash": row["code_hash"], "p_session_hash": "f" * 64}) is None


@pytest.mark.parametrize("authorization", [None, "Bearer legacy", "Bearer v2.legacy.signature", "Bearer supabase-jwt", "Bearer sf_owner_v2_" + "A" * 43])
def test_legacy_and_unknown_tokens_rejected(setup, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    assert setup[3].get("/auth/owner-v2/session", headers=headers).status_code == 401


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_public_and_runtime_roles_cannot_bootstrap(setup, role):
    with pytest.raises(RuntimeError, match="permission denied"):
        setup[0].query("select public.owner_v2_bootstrap($1,$2)", [OWNER, EMAIL], role)


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_client_roles_cannot_access_tables_or_auth_rpcs(setup, role):
    db = setup[0]
    for table in ["soloforge_owners", "soloforge_owner_accounts", "owner_v2_challenges", "owner_v2_sessions"]:
        with pytest.raises(RuntimeError, match="permission denied"):
            db.query(f"select * from public.{table}", role=role)
        assert db.query("select relrowsecurity from pg_class where relname=$1", [table])[0]["relrowsecurity"]
    with pytest.raises(RuntimeError, match="permission denied"):
        db.query("select public.owner_v2_session_identity($1)", ["a" * 64], role)


def test_seed_is_idempotent_and_identity_immutable(setup):
    db = setup[0]
    before = db.query("select * from public.soloforge_owners")
    db.query("select public.owner_v2_bootstrap($1,$2)", [OWNER, EMAIL])
    assert db.query("select * from public.soloforge_owners") == before
    with pytest.raises(RuntimeError, match="already locked"):
        db.query("select public.owner_v2_bootstrap($1,$2)", [str(uuid4()), EMAIL])
    for sql in ["update public.soloforge_owners set primary_email='other@example.test'",
                "delete from public.soloforge_owners",
                "update public.soloforge_owners set owner_id='22222222-2222-4222-8222-222222222222'"]:
        with pytest.raises(RuntimeError, match="immutable"):
            db.query(sql)
    with pytest.raises(RuntimeError, match="permission denied"):
        db.query("update public.soloforge_owners set primary_email='other@example.test'", role="service_role")
    accounts = db.query("select * from public.soloforge_owner_accounts")
    assert len(accounts) == 3
    assert all(r["provider_account_id"] is None and r["verification_status"] == "pending" and r["verified_at"] is None for r in accounts)


def test_unsubstantiated_provider_verification_rejected(setup):
    with pytest.raises(RuntimeError, match="check constraint"):
        setup[0].query("update public.soloforge_owner_accounts set verification_status='verified'")


def test_missing_smtp_configuration_prevents_db_call(setup, monkeypatch):
    db = setup[0]
    monkeypatch.delenv("OWNER_V2_SMTP_HOST", raising=False)
    with pytest.raises(auth.Unavailable):
        auth.OwnerV2(db.call).request(EMAIL)
    assert not db.calls


def test_transport_failure_sanitized_without_retry(monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(args)
        raise RuntimeError("secret-provider-response")
    monkeypatch.setattr(auth, "supabase_request", fail)
    with pytest.raises(auth.Unavailable) as exc:
        auth.rpc("session_identity", {"p_session_hash": "a" * 64})
    assert "secret" not in str(exc.value) and len(calls) == 1


def test_ambiguous_consumption_is_not_retried(setup):
    db, mail, service, client = setup
    body = proof(setup)
    def lost(name, data):
        db.call(name, data)
        raise auth.Unavailable("Owner V2 is unavailable")
    ambiguous = auth.OwnerV2(lost, lambda: mail)
    with pytest.raises(auth.Unavailable):
        ambiguous.verify(**body)
    assert client.post("/auth/owner-v2/verify", json=body).status_code == 401
    assert len(db.query("select * from public.owner_v2_sessions")) == 1


def test_no_legacy_identity_imports_or_execution_scopes():
    source = Path(auth.__file__).read_text()
    for forbidden in ["soloforge_session", "pollinations_sessions", "owner_provider_bindings", "owner_provider_key_rotations", "SOLOFORGE_SESSION_SECRET", "SOLOFORGE_TRUSTED_BINDING", "POLLINATIONS_API_KEY"]:
        assert forbidden not in source
    assert "scope" not in auth.OwnerV2._identity({"owner_id": OWNER, "primary_email": EMAIL, "status": "active"})


def test_smtp_uses_verified_tls_and_sends_only_to_registry_email(monkeypatch):
    for key, value in {"HOST": "smtp.example.test", "USERNAME": "test-user", "PASSWORD": "test-only-password", "FROM": "login@example.test"}.items():
        monkeypatch.setenv("OWNER_V2_SMTP_" + key, value)
    calls = []
    class SMTP:
        def __init__(self, host, port, *, timeout, context):
            assert (host, port, timeout) == ("smtp.example.test", 465, 15)
            assert context.check_hostname and context.verify_mode == auth.ssl.CERT_REQUIRED
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def login(self, user, password): calls.append((user, password))
        def send_message(self, message):
            assert message["To"] == EMAIL and message["From"] == "login@example.test"
            assert "A" * 43 in message.get_content()
            calls.append("send")
            return {}
    monkeypatch.setattr(auth.smtplib, "SMTP_SSL", SMTP)
    auth.SMTPDelivery().send(EMAIL, "A" * 43)
    assert calls == [("test-user", "test-only-password"), "send"]


def test_http_never_accepts_identity_or_scope_from_client(setup):
    client = setup[3]
    r = client.post("/auth/owner-v2/request", json={"email": EMAIL, "owner_id": OWNER, "scope": "publish"})
    assert r.status_code == 422
    assert not setup[0].calls and not setup[1].messages


def test_invalid_session_insert_rolls_back_consumption(setup):
    db = setup[0]
    body = proof(setup)
    with pytest.raises(RuntimeError, match="check constraint"):
        db.call("consume_challenge", {"p_challenge_id": body["challenge_id"], "p_browser_hash": auth.digest(body["browser_proof"]),
            "p_code_hash": auth.digest(body["code"]), "p_session_hash": "invalid"})
    row = db.query("select consumed_at, attempts from public.owner_v2_challenges")[0]
    assert row == {"consumed_at": None, "attempts": 0}
    assert setup[3].post("/auth/owner-v2/verify", json=body).status_code == 200


def test_account_app_metadata_is_rejected_not_inferred(setup):
    db = setup[0]
    db.query("truncate public.owner_v2_sessions,public.owner_v2_challenges,public.soloforge_owner_accounts,public.soloforge_owners")
    with pytest.raises(RuntimeError, match="confirmed account metadata"):
        db.query("select public.owner_v2_bootstrap($1,$2,$3)", [OWNER, EMAIL, json.dumps({"pollinations": {"client_id": "not-an-account"}})])
    assert db.query("select * from public.soloforge_owners") == []


def test_runtime_cannot_insert_or_delete_owner(setup):
    db = setup[0]
    for sql in ["insert into public.soloforge_owners(owner_id,primary_email) values ('22222222-2222-4222-8222-222222222222','other@example.test')",
                "delete from public.soloforge_owners"]:
        with pytest.raises(RuntimeError, match="permission denied"):
            db.query(sql, role="service_role")


def test_session_tamper_and_epoch_revocation(setup):
    db, mail, service, client = setup
    token = login(setup)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(auth.Unauthorized): service.authenticate("Bearer " + tampered)
    db.query("update public.soloforge_owners set auth_epoch=auth_epoch+1", role="service_role")
    with pytest.raises(auth.Unauthorized): service.authenticate("Bearer " + token)
    with pytest.raises(RuntimeError, match="cannot decrease"):
        db.query("update public.soloforge_owners set auth_epoch=0", role="service_role")


def test_malformed_rpc_response_fails_closed(setup):
    service = auth.OwnerV2(lambda *args: {"owner_id": "broken", "status": "active"})
    with pytest.raises(auth.Unavailable):
        service.authenticate("Bearer sf_owner_v2_" + "A" * 43)


def test_main_mounts_v2_without_enabling_it(monkeypatch):
    # Import production entrypoint under the network-denying offline runner.
    from backend.asset_forge import main
    monkeypatch.delenv("OWNER_V2_AUTH_ENABLED", raising=False)
    client = TestClient(main.app)
    assert client.post("/auth/owner-v2/request", json={"email": EMAIL}).status_code == 503
    assert client.get("/health").status_code == 200
    from backend import execution_policy
    assert not execution_policy.generation_execution_authorized()


def test_v2_token_is_rejected_by_legacy_session_authority(setup, monkeypatch):
    from backend.asset_forge.backend import soloforge_session as legacy
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", OWNER)
    monkeypatch.setenv("SOLOFORGE_SESSION_SECRET", "test-only-legacy-signing-key-do-not-use")
    assert not legacy.validate_session_token(login(setup))


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_all_v2_function_and_table_acl_boundaries(setup, role):
    db = setup[0]
    functions = db.query("select oid::regprocedure::text as signature from pg_proc where proname like 'owner_v2_%'")
    assert len(functions) == 7
    for function in functions:
        assert db.query("select has_function_privilege($1,$2,'EXECUTE') as allowed", [role, function["signature"]])[0]["allowed"] is False
    for table in ["soloforge_owners", "soloforge_owner_accounts", "owner_v2_challenges", "owner_v2_sessions"]:
        for privilege in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]:
            assert db.query("select has_table_privilege($1,$2,$3) as allowed", [role, "public." + table, privilege])[0]["allowed"] is False


def test_registry_null_email_and_disabled_owner_cannot_request(setup):
    db, mail, service, client = setup
    assert db.call("reserve_challenge", {"p_email": None, "p_challenge_id": str(uuid4()),
        "p_code_hash": "a" * 64, "p_browser_hash": "b" * 64}) is None
    db.query("update public.soloforge_owners set status='disabled'")
    assert client.post("/auth/owner-v2/request", json={"email": EMAIL}).status_code == 202
    assert not mail.messages and not db.query("select * from public.owner_v2_challenges")


@pytest.mark.parametrize("method,path,body", [
    ("post", "/auth/owner-v2/request", {"email": EMAIL}),
    ("post", "/auth/owner-v2/verify", {"challenge_id": str(uuid4()), "browser_proof": "A" * 43, "code": "B" * 43}),
    ("get", "/auth/owner-v2/session", None),
    ("post", "/auth/owner-v2/logout", None),
])
def test_every_route_disabled_without_storage_or_delivery(setup, monkeypatch, method, path, body):
    db, mail, service, client = setup
    monkeypatch.delenv("OWNER_V2_AUTH_ENABLED", raising=False)
    kwargs = {"headers": {"Authorization": "Bearer sf_owner_v2_" + "A" * 43}}
    if body is not None:
        kwargs["json"] = body
    result = getattr(client, method)(path, **kwargs)
    assert result.status_code == 503
    assert result.headers["cache-control"] == "no-store"
    assert not db.calls and not mail.messages


@pytest.mark.parametrize("row", [False, [], {}, {"primary_email": "other@example.test"}])
def test_malformed_reservation_never_delivers_or_activates(monkeypatch, row):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    calls, mail = [], Mailbox()
    def call(name, body):
        calls.append(name)
        return row
    with pytest.raises(auth.Unavailable):
        auth.OwnerV2(call, lambda: mail).request(EMAIL)
    assert calls == ["reserve_challenge"] and not mail.messages


def test_delivery_activation_failure_keeps_challenge_unusable(setup):
    db, mail, service, client = setup
    def call(name, body):
        if name == "activate_challenge":
            return False
        return db.call(name, body)
    with pytest.raises(auth.Unavailable):
        auth.OwnerV2(call, lambda: mail).request(EMAIL)
    challenge = db.query("select * from public.owner_v2_challenges")[0]
    assert challenge["delivered_at"] is None and len(mail.messages) == 1
    assert db.call("consume_challenge", {
        "p_challenge_id": challenge["challenge_id"], "p_browser_hash": challenge["browser_hash"],
        "p_code_hash": challenge["code_hash"], "p_session_hash": "a" * 64,
    }) is None


def test_runtime_cannot_change_provider_identity_or_verification(setup):
    db = setup[0]
    for statement in [
        "update public.soloforge_owner_accounts set provider_account_id='untrusted'",
        "update public.soloforge_owner_accounts set verification_status='mismatch'",
        "delete from public.soloforge_owner_accounts",
    ]:
        with pytest.raises(RuntimeError, match="permission denied"):
            db.query(statement, role="service_role")


@pytest.mark.parametrize("variant", [
    "missing_challenge", "missing_code", "missing_browser", "short_code",
    "long_browser", "invalid_challenge_type", "extra_field", "invalid_json",
])
def test_v2_validation_errors_do_not_reflect_proofs(setup, variant):
    db, mail, service, client = setup
    code, browser = "S" * 43, "P" * 43
    body = {"challenge_id": str(uuid4()), "code": code, "browser_proof": browser}
    if variant.startswith("missing_"):
        body.pop({"missing_challenge": "challenge_id", "missing_code": "code",
                  "missing_browser": "browser_proof"}[variant])
    elif variant == "short_code":
        body["code"] = code[:-1]
    elif variant == "long_browser":
        body["browser_proof"] = browser + "P"
    elif variant == "invalid_challenge_type":
        body["challenge_id"] = {"code": code, "browser_proof": browser}
    elif variant == "extra_field":
        body["unexpected"] = {"code": code, "browser_proof": browser}
    if variant == "invalid_json":
        result = client.post("/auth/owner-v2/verify", content=json.dumps(body)[:-1],
                             headers={"Content-Type": "application/json"})
    else:
        result = client.post("/auth/owner-v2/verify", json=body)
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid input"}
    assert result.headers["cache-control"] == "no-store"
    assert code[:-1] not in result.text and browser not in result.text
    assert not db.calls and not mail.messages


def test_v2_request_validation_sanitized_even_when_disabled(setup, monkeypatch):
    db, mail, service, client = setup
    monkeypatch.delenv("OWNER_V2_AUTH_ENABLED", raising=False)
    result = client.post("/auth/owner-v2/request", json={
        "email": EMAIL, "code": "S" * 43, "browser_proof": "P" * 43,
    })
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid input"}
    assert result.headers["cache-control"] == "no-store"
    assert not db.calls and not mail.messages


def test_v2_validation_handler_preserves_unrelated_routes():
    app = FastAPI()
    app.include_router(routes.router)

    @app.post("/unrelated")
    def unrelated(body: routes.EmailRequest):
        return {"accepted": True}

    with TestClient(app) as client:
        result = client.post("/unrelated", json={})
    assert result.status_code == 422
    assert isinstance(result.json()["detail"], list)
    assert result.json()["detail"][0]["loc"] == ["body", "email"]
    assert "cache-control" not in result.headers



def test_github_bridge_requires_verified_supabase_binding(setup):
    db, mail, service, client = setup
    supabase_id = "22222222-2222-4222-8222-222222222222"
    db.query("update public.soloforge_owner_accounts set provider_account_id=$1 where provider='supabase'", [supabase_id])
    with pytest.raises(auth.Unauthorized):
        service.github_session(supabase_id)
    assert db.query("select * from public.owner_v2_sessions") == []
    db.query("""update public.soloforge_owner_accounts
                set verification_status='verified', verified_at=clock_timestamp(),
                    verification_evidence='offline independently verified owner'
                where provider='supabase'""")
    with pytest.raises(auth.Unauthorized):
        service.github_session("33333333-3333-4333-8333-333333333333")
    result = service.github_session(supabase_id)
    assert result["session_token"].startswith("sf_owner_v2_")
    assert service.authenticate("Bearer " + result["session_token"])["owner_id"] == OWNER
    db.query("update public.soloforge_owners set status='disabled'")
    with pytest.raises(auth.Unauthorized):
        service.github_session(supabase_id)
    with pytest.raises(auth.Unauthorized):
        service.authenticate("Bearer " + result["session_token"])
