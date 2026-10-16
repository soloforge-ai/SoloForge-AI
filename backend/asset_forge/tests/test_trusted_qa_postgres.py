"""Real PostgreSQL multi-connection security/concurrency tests; disposable CI only."""
import os
import pathlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("QA_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="Disposable PostgreSQL required")
MIGRATION = pathlib.Path(__file__).resolve().parents[3] / "supabase/migrations/202610160001_qa_trusted_evidence_preparation.sql"

@pytest.fixture(scope="module", autouse=True)
def schema():
    if not DSN:
        yield
        return
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("CREATE ROLE service_role NOLOGIN")
        conn.execute("CREATE ROLE authenticated NOLOGIN")
        conn.execute("CREATE ROLE anon NOLOGIN")
        conn.execute("GRANT service_role, authenticated, anon TO postgres")
        conn.execute(MIGRATION.read_text())
        conn.execute("GRANT USAGE ON SCHEMA public TO service_role, authenticated, anon")
    yield

def seed():
    grant, evidence = str(uuid.uuid4()), str(uuid.uuid4())
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("""INSERT INTO public.qa_reviewer_grants
          (grant_id,principal_id,job_id,revision_id,allowed_stages,expires_at)
          VALUES (%s,'reviewer','job','rev',ARRAY['CONTENT'],now()+interval '1 day')""",(grant,))
        conn.execute("""INSERT INTO public.qa_trusted_evidence
          (evidence_id,job_id,stage,revision_id,principal_id,grant_id,
           input_sha256,output_sha256,input_artifact_ref,output_artifact_ref,key_id,signature)
          VALUES (%s,'job','CONTENT','rev','reviewer',%s,%s,%s,'immutable:in','immutable:out','k1',%s)""",
          (evidence,grant,'a'*64,'b'*64,'c'*64))
    return grant,evidence

def claim(eid, cid=None, *, job="job", principal="reviewer"):
    with psycopg.connect(DSN) as conn:
        conn.execute("SET LOCAL ROLE service_role")
        return conn.execute(
          "SELECT public.qa_claim_verified_evidence(%s,%s,%s,%s,%s,%s)",
          (eid,cid or str(uuid.uuid4()),job,"rev","CONTENT",principal)).fetchone()[0]

def revoke(gid):
    with psycopg.connect(DSN) as conn:
        conn.execute("SET LOCAL ROLE service_role")
        return conn.execute("SELECT public.qa_revoke_reviewer_grant(%s)",(gid,)).fetchone()[0]

def test_single_claim_and_audit():
    _,eid=seed()
    assert claim(eid) is True
    assert claim(eid) is False
    with psycopg.connect(DSN) as conn:
        assert conn.execute("SELECT count(*) FROM public.qa_evidence_replay_claims WHERE evidence_id=%s",(eid,)).fetchone()[0]==1
        assert conn.execute("SELECT count(*) FROM public.qa_evidence_audit WHERE evidence_id=%s AND event_type='CLAIMED'",(eid,)).fetchone()[0]==1

def test_parallel_claim_exactly_one():
    _,eid=seed()
    barrier=threading.Barrier(8)
    def contender(_):
        barrier.wait(timeout=15)
        return claim(eid)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(contender,range(8)))
    assert results.count(True)==1
    assert results.count(False)==7

def test_cross_job_and_principal_blocked():
    _,eid=seed()
    assert claim(eid,job="other") is False
    assert claim(eid,principal="other") is False
    assert claim(eid) is True

def test_revocation_blocks_claim():
    gid,eid=seed()
    assert revoke(gid) is True
    assert revoke(gid) is False
    assert claim(eid) is False

def test_expiry_blocks_claim():
    gid,eid=seed()
    with psycopg.connect(DSN,autocommit=True) as conn:
        conn.execute("UPDATE public.qa_reviewer_grants SET expires_at=now()-interval '1 second' WHERE grant_id=%s",(gid,))
    assert claim(eid) is False

def test_revocation_claim_serialization():
    gid,eid=seed()
    # Hold grant lock; claim and revoke must serialize, not bypass the lock.
    with psycopg.connect(DSN) as holder:
        holder.execute("SELECT 1 FROM public.qa_reviewer_grants WHERE grant_id=%s FOR UPDATE",(gid,))
        started=threading.Event()
        def worker():
            started.set()
            return revoke(gid)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(worker)
            assert started.wait(5)
            holder.execute("UPDATE public.qa_reviewer_grants SET revoked_at=now() WHERE grant_id=%s",(gid,))
            holder.commit()
            assert future.result(timeout=15) is False
    assert claim(eid) is False

def test_anon_authenticated_no_rpc_or_dml():
    gid,eid=seed()
    for role in ("anon","authenticated"):
        with psycopg.connect(DSN) as conn:
            conn.execute("SET LOCAL ROLE "+role)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT public.qa_claim_verified_evidence(%s,%s,'job','rev','CONTENT','reviewer')",(eid,str(uuid.uuid4())))
            conn.rollback()
        with psycopg.connect(DSN) as conn:
            conn.execute("SET LOCAL ROLE "+role)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT * FROM public.qa_trusted_evidence")

def test_service_role_no_direct_dml():
    _,eid=seed()
    with psycopg.connect(DSN) as conn:
        conn.execute("SET LOCAL ROLE service_role")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM public.qa_trusted_evidence WHERE evidence_id=%s",(eid,))
