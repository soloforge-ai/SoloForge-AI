"""Disposable PostgreSQL integration tests for PR #192. No network/provider calls."""
import concurrent.futures
from decimal import Decimal
import os
import threading
import uuid

import psycopg
import pytest

DSN = os.environ["TEST_DATABASE_URL"]
MODEL = "black-forest-labs/flux.1-kontext-pro"
HASH = "a" * 64


def connect(role="service_role"):
    c = psycopg.connect(DSN, autocommit=True, connect_timeout=5)
    c.execute("SET statement_timeout = '10000ms'")
    c.execute("SET lock_timeout = '5000ms'")
    c.execute("SELECT set_config('request.jwt.claim.role', %s, false)", (role,))
    if role in ('anon', 'authenticated'):
        c.execute('SET ROLE ' + role)
    return c


@pytest.fixture
def allocation():
    with connect() as c:
        owner = str(uuid.uuid4())
        allocation_id = c.execute(
            """INSERT INTO public.manual_qa_allocations
            (owner_id,wallet_binding_ref,provider_model,authorized_budget,expires_at)
            VALUES (%s,'wallet-test-only',%s,1,now()+interval '1 hour')
            RETURNING id""", (owner, MODEL)).fetchone()[0]
    return allocation_id


def claim(c, allocation_id, key=None, cost="0.6", digest=HASH, model=MODEL):
    return c.execute(
        "SELECT * FROM public.manual_qa_claim(%s,%s,%s,%s,%s)",
        (allocation_id, key or uuid.uuid4().hex, digest, model, cost),
    ).fetchone()


def test_migration_schema_and_rpc():
    with connect() as c:
        tables = {r[0] for r in c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        )}
        assert {"manual_qa_allocations", "manual_qa_requests"} <= tables
        for table in ("manual_qa_allocations", "manual_qa_requests"):
            assert c.execute(
                "SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass",
                (f"public.{table}",),
            ).fetchone()[0]


def test_idempotency_and_conflict(allocation):
    key = uuid.uuid4().hex
    with connect() as c:
        first = claim(c, allocation, key)
        second = claim(c, allocation, key)
        assert first[1] is True and second == (first[0], False, "CALL_STARTED")
        with pytest.raises(psycopg.Error):
            claim(c, allocation, key, digest="b" * 64)
        assert c.execute(
            "SELECT reserved_budget FROM public.manual_qa_allocations WHERE id=%s",
            (allocation,),
        ).fetchone()[0] == Decimal('0.6')


def test_concurrent_distinct_keys_budget(allocation):
    barrier = threading.Barrier(2)
    def run(_):
        with connect() as c:
            barrier.wait(timeout=5)
            try:
                return claim(c, allocation)[1]
            except psycopg.Error:
                return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(results) == [False, True]
    with connect() as c:
        assert c.execute(
            "SELECT count(*) FROM public.manual_qa_requests WHERE allocation_id=%s",
            (allocation,),
        ).fetchone()[0] == 1


def test_concurrent_same_key_dispatch_once(allocation):
    key = uuid.uuid4().hex
    barrier = threading.Barrier(2)
    def run(_):
        with connect() as c:
            barrier.wait(timeout=5)
            return claim(c, allocation, key)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sum(bool(r[1]) for r in results) == 1
    assert results[0][0] == results[1][0]


def test_settlement_and_ambiguous_hold(allocation):
    with connect() as c:
        first = claim(c, allocation, cost="0.4")
        assert c.execute(
            "SELECT public.manual_qa_settle(%s,'RECONCILIATION_REQUIRED',null)",
            (first[0],),
        ).fetchone()[0] == "RECONCILIATION_REQUIRED"
        assert claim(c, allocation, cost="0.6")[1] is True
        with pytest.raises(psycopg.Error):
            c.execute("SELECT public.manual_qa_settle(%s,'SUCCEEDED',0.1)", (first[0],))
        amounts = c.execute(
            "SELECT reserved_budget,consumed_budget FROM public.manual_qa_allocations WHERE id=%s",
            (allocation,),
        ).fetchone()
        assert amounts == (1, 0)


def test_successful_settlement(allocation):
    with connect() as c:
        first = claim(c, allocation, cost="0.6")
        assert c.execute(
            "SELECT public.manual_qa_settle(%s,'SUCCEEDED',0.2)", (first[0],)
        ).fetchone()[0] == "SUCCEEDED"
        assert c.execute(
            "SELECT reserved_budget,consumed_budget FROM public.manual_qa_allocations WHERE id=%s",
            (allocation,),
        ).fetchone() == (Decimal('0'), Decimal('0.2'))


def test_invalid_model_and_expired_allocation(allocation):
    with connect() as c:
        with pytest.raises(psycopg.Error):
            claim(c, allocation, model="wrong-model")
        c.execute("UPDATE public.manual_qa_allocations SET expires_at=now()-interval '1 second' WHERE id=%s", (allocation,))
        with pytest.raises(psycopg.Error):
            claim(c, allocation)


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_client_rpc_denied(role, allocation):
    with connect(role) as c:
        with pytest.raises(psycopg.Error):
            claim(c, allocation)
        with pytest.raises(psycopg.Error):
            c.execute("SELECT * FROM public.manual_qa_allocations")


def test_revoke_and_direct_dml_denied(allocation):
    with connect() as c:
        c.execute("UPDATE public.manual_qa_allocations SET revoked_at=now() WHERE id=%s", (allocation,))
        with pytest.raises(psycopg.Error):
            claim(c, allocation)
    with connect("authenticated") as c:
        with pytest.raises(psycopg.Error):
            c.execute("INSERT INTO public.manual_qa_requests DEFAULT VALUES")


def test_lock_order_concurrency(allocation):
    """Expose claim allocation->request versus settle request->allocation deadlock."""
    with connect() as c:
        first = claim(c, allocation, key="deadlock-first-key-00001", cost="0.2")
    a = connect()
    b = connect()
    try:
        a.autocommit = False
        b.autocommit = False
        a.execute("SELECT id FROM public.manual_qa_allocations WHERE id=%s FOR UPDATE", (allocation,))
        barrier = threading.Barrier(2)
        def settle():
            barrier.wait(timeout=5)
            try:
                b.execute("SELECT public.manual_qa_settle(%s,'SUCCEEDED',0.1)", (first[0],))
                b.commit()
                return "ok"
            except psycopg.Error as exc:
                b.rollback()
                return exc.sqlstate
        def second_claim():
            barrier.wait(timeout=5)
            try:
                claim(a, allocation, "deadlock-second-key-0002", "0.2")
                a.commit()
                return "ok"
            except psycopg.Error as exc:
                a.rollback()
                return exc.sqlstate
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            fa = pool.submit(second_claim)
            fb = pool.submit(settle)
            results = [fa.result(timeout=15), fb.result(timeout=15)]
        assert results == ["ok", "ok"], f"locking conflict: {results}"
    finally:
        a.close()
        b.close()
