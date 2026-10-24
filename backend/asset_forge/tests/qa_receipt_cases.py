"""Disposable PostgreSQL receipt transaction and replay/concurrency tests."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import psycopg
import pytest
from backend.asset_forge.tests.test_trusted_qa_postgres import DSN, seed_chain

pytestmark = pytest.mark.skipif(not DSN, reason="Disposable PostgreSQL required")
@pytest.fixture(scope="module", autouse=True)
def setup_receipt():
    # Existing test module owns disposable schema setup; run its fixture first
    from backend.asset_forge.tests.test_trusted_qa_postgres import schema
    # Pytest autouse schema in imported test module may not run for this file;
    # this suite is imported by the original test module below instead.
    yield

def insert_receipt(ids, *, expiry="1 hour", digest="a"*64):
    rid,cid=str(uuid.uuid4()),str(uuid.uuid4())
    with psycopg.connect(DSN,autocommit=True) as c:
        c.execute("""insert into public.qa_verification_receipts
        (receipt_id,chain_claim_id,job_id,revision_id,route,evidence_ids,
         artifact_digest,issuer_id,issued_at,expires_at)
        values (%s,%s,'chain-job','chain-rev','IMAGE',%s,%s,'fixture-only',
        now(),now()+(%s)::interval)""",
        (rid,cid,[e for _,e in ids],digest,expiry))
    return rid,cid

def consume(ids,rid,cid,*,digest="a"*64):
    with psycopg.connect(DSN) as c:
        return c.execute("""select public.qa_claim_chain_with_receipt(
        %s,%s,'chain-job','chain-rev','IMAGE',%s,%s)""",
        (rid,cid,[e for _,e in ids],digest)).fetchone()[0]

def test_receipt_parallel_single_winner():
    ids=seed_chain();rid,cid=insert_receipt(ids)
    barrier=threading.Barrier(6)
    def worker(_):
        barrier.wait(timeout=15)
        return consume(ids,rid,cid)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(worker,range(6)))
    assert results.count(True)==1 and results.count(False)==5

def test_receipt_digest_mismatch_does_not_consume():
    ids=seed_chain();rid,cid=insert_receipt(ids)
    assert consume(ids,rid,cid,digest="b"*64) is False
    assert consume(ids,rid,cid) is True

def test_receipt_expired_and_revoked_blocked():
    for revoke in (False,True):
        ids=seed_chain();rid,cid=insert_receipt(ids,expiry="1 hour")
        with psycopg.connect(DSN,autocommit=True) as c:
            if revoke:
                c.execute("update public.qa_verification_receipts set revoked_at=now() where receipt_id=%s",(rid,))
            else:
                c.execute("update public.qa_verification_receipts set expires_at=now()-interval '1 second' where receipt_id=%s",(rid,))
        assert consume(ids,rid,cid) is False

def test_receipt_role_denied():
    ids=seed_chain();rid,cid=insert_receipt(ids)
    with psycopg.connect(DSN) as c:
        c.execute("set local role service_role")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("""select public.qa_claim_chain_with_receipt(
              %s,%s,'chain-job','chain-rev','IMAGE',%s,%s)""",
              (rid,cid,[e for _,e in ids],"a"*64))
