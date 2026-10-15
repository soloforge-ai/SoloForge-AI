"""Disposable PostgreSQL 16 concurrency tests; never connect to production."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

DSN = os.environ.get("SOLOFORGE_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="Disposable PostgreSQL DSN required")


def connection():
    db = psycopg.connect(DSN, autocommit=True)
    db.execute("select set_config('request.jwt.claim.role','service_role',false)")
    return db


def issue(kind, digest, owner, payload='{"value":"synthetic"}'):
    with connection() as db:
        return db.execute(
            "select public.pollinations_oauth_issue(%s,%s,%s,%s::jsonb,now()+interval '5 minutes')",
            (kind, digest, owner, payload),
        ).fetchone()[0]


def consume(kind, digest, owner):
    with connection() as db:
        return db.execute("select public.pollinations_oauth_consume(%s,%s,%s)",
                          (kind, digest, owner)).fetchone()[0]


@pytest.mark.parametrize("kind", ["login_ticket", "pkce_state", "mobile_handoff"])
def test_atomic_concurrent_claim_and_replay(kind):
    owner = os.environ["SOLOFORGE_TEST_OWNER_UUID"]
    digest = uuid.uuid4().hex * 2
    assert issue(kind, digest, owner)
    barrier = Barrier(12)

    def compete(_):
        barrier.wait(timeout=15)
        return consume(kind, digest, owner)

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(compete, range(12)))
    assert sum(item is not None for item in results) == 1
    assert consume(kind, digest, owner) is None


def test_owner_mismatch_does_not_consume_claim():
    owner = os.environ["SOLOFORGE_TEST_OWNER_UUID"]
    other = os.environ["SOLOFORGE_TEST_OTHER_UUID"]
    digest = uuid.uuid4().hex * 2
    issue("mobile_handoff", digest, owner)
    assert consume("mobile_handoff", digest, other) is None
    assert consume("mobile_handoff", digest, owner) == {"value": "synthetic"}


def test_expired_claim_denied():
    owner = os.environ["SOLOFORGE_TEST_OWNER_UUID"]
    digest = uuid.uuid4().hex * 2
    issue("pkce_state", digest, owner)
    with connection() as db:
        db.execute("update public.pollinations_oauth_claims set expires_at=now()-interval '1 second' where claim_hash=%s", (digest,))
    assert consume("pkce_state", digest, owner) is None


def test_unprivileged_role_denied():
    owner = os.environ["SOLOFORGE_TEST_OWNER_UUID"]
    digest = uuid.uuid4().hex * 2
    with psycopg.connect(DSN, autocommit=True) as db:
        db.execute("select set_config('request.jwt.claim.role','authenticated',false)")
        with pytest.raises(psycopg.Error):
            db.execute("select public.pollinations_oauth_issue(%s,%s,%s,'{}'::jsonb,now()+interval '5 minutes')",
                       ("login_ticket", digest, owner))
