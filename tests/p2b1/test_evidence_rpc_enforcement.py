"""Fail-closed RPC boundary negative tests; no provider calls, no issuer."""
import os
from datetime import datetime, timedelta, timezone
import uuid
import pytest
psycopg=pytest.importorskip("psycopg")
pytestmark=pytest.mark.skipif(not os.getenv("P2B1_TEST_DSN"),reason="disposable DB missing")
from test_phase1_concurrency import seed,approval,reserve,connect,uid

def scenario():
    data=seed()
    eid=reserve(data,approval(data,5),uid())
    with connect() as c:
        rid=c.execute("select id from public.generation_requests where execution_id=%s order by slide_ordinal limit 1",(eid,)).fetchone()[0]
        c.execute("set role service_role")
        assert c.execute("select public.generation_mark_call_started(%s,%s,%s)",(rid,data[0],data[2])).fetchone()[0]
    return data,eid,rid

def issue_fixture(data,eid,rid,ref="verified",expiry=3600):
    with connect() as c:
        c.execute("""insert into generation_evidence.verified_results(
          execution_id,request_id,owner_user_id,pollinations_session_id,
          provider_request_ref,authorization_ref,evidence_ref,evidence_sha256,
          outcome,observed_pollen,issuer_id,verified_at,expires_at)
          values(%s,%s,%s,%s,%s,'synthetic-allocation',%s,%s,'SUCCEEDED',1,
          'disposable-ci-only',now()-interval '1 minute',now()+(%s || ' seconds')::interval)""",
          (eid,rid,data[0],data[2],uid(),ref,'f'*64,expiry))

def terminal(data,rid,ref):
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            c.execute("""select public.generation_record_verified_result(
              %s,%s,%s,'SUCCEEDED',%s,1,'test',%s,'v1',%s)""",
              (rid,data[0],data[2],ref,str(rid),'c'*64))

def test_missing_evidence_rejected():
    d,e,r=scenario()
    terminal(d,r,"missing")

def test_forged_evidence_reference_rejected():
    d,e,r=scenario()
    issue_fixture(d,e,r)
    terminal(d,r,"forged")

def test_expired_evidence_rejected():
    d,e,r=scenario()
    issue_fixture(d,e,r,expiry=-1)
    terminal(d,r,"verified")

def test_cross_execution_evidence_rejected():
    d,e,r=scenario()
    other,other_e,other_r=scenario()
    issue_fixture(other,other_e,other_r)
    terminal(d,r,"verified")

def test_valid_synthetic_registry_record_allows_terminal_result():
    d,e,r=scenario()
    issue_fixture(d,e,r)
    with connect() as c:
        c.execute("set role service_role")
        assert c.execute("""select public.generation_record_verified_result(
          %s,%s,%s,'SUCCEEDED','verified',1,'test',%s,'v1',%s)""",
          (r,d[0],d[2],str(r),'c'*64)).fetchone()[0]

def test_settlement_and_recovery_without_verified_evidence_fail_closed():
    d,e,r=scenario()
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_settle_execution(%s,%s,%s,0,'missing')",(e,d[0],d[2]))
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_resume_after_reconciliation(%s,%s,%s,'missing')",(e,d[0],d[2]))


def complete_four_verified_slides(data, eid, expiry=3600):
    """Synthetic admin-issued fixtures; never a production issuer."""
    with connect() as c:
        rows=c.execute("""select id from public.generation_requests
          where execution_id=%s order by slide_ordinal""",(eid,)).fetchall()
    for i,(rid,) in enumerate(rows):
        ref=f"verified-{eid}-{i}"
        issue_fixture(data,eid,rid,ref=ref,expiry=expiry)
        with connect() as c:
            c.execute("set role service_role")
            assert c.execute("select public.generation_mark_call_started(%s,%s,%s)",
                             (rid,data[0],data[2])).fetchone()[0]
            assert c.execute("""select public.generation_record_verified_result(
              %s,%s,%s,'SUCCEEDED',%s,1,'test',%s,'v1',%s)""",
              (rid,data[0],data[2],ref,str(rid),'c'*64)).fetchone()[0]
    return f"verified-{eid}-0"


def settle(data,eid,ref):
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_settle_execution(%s,%s,%s,4,%s)",
                      (eid,data[0],data[2],ref))
    with connect() as c:
        assert c.execute("""select count(*) from public.generation_budget_ledger
          where execution_id=%s and entry_kind='SETTLE'""",(eid,)).fetchone()[0]==0


def test_settlement_expired_result_evidence_rejected():
    import time
    data=seed()
    eid=reserve(data,approval(data,5),uid())
    ref=complete_four_verified_slides(data,eid,expiry=1)
    time.sleep(1.5)
    settle(data,eid,ref)


def test_settlement_cross_execution_evidence_reference_rejected():
    data=seed()
    eid=reserve(data,approval(data,5),uid())
    own_ref=complete_four_verified_slides(data,eid)
    other=seed()
    other_eid=reserve(other,approval(other,5),uid())
    foreign_ref=complete_four_verified_slides(other,other_eid)
    settle(data,eid,foreign_ref)
    # Correct execution-scoped evidence remains accepted in the synthetic fixture.
    with connect() as c:
        c.execute("set role service_role")
        assert c.execute("select public.generation_settle_execution(%s,%s,%s,4,%s)",
                         (eid,data[0],data[2],own_ref)).fetchone()[0]


def reconciled_synthetic_execution(expiry=3600):
    data,eid,rid=scenario()
    with connect() as c:
        c.execute("set role service_role")
        assert c.execute("""select public.generation_record_verified_result(
          %s,%s,%s,'UNKNOWN_RECONCILE','uncertain',0)""",
          (rid,data[0],data[2])).fetchone()[0]
    ref=f"reconciled-{eid}"
    issue_fixture(data,eid,rid,ref=ref,expiry=expiry)
    with connect() as c:
        c.execute("set role service_role")
        assert c.execute("""select public.generation_record_verified_result(
          %s,%s,%s,'SUCCEEDED',%s,1,'test',%s,'v1',%s)""",
          (rid,data[0],data[2],ref,str(rid),'c'*64)).fetchone()[0]
    return data,eid,ref


def recover_denied(data,eid,ref):
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_resume_after_reconciliation(%s,%s,%s,%s)",
                      (eid,data[0],data[2],ref))
    with connect() as c:
        assert c.execute("select state from public.generation_executions where id=%s",
                         (eid,)).fetchone()[0]=="UNKNOWN_RECONCILE"


def test_recovery_expired_verified_evidence_rejected():
    import time
    data,eid,ref=reconciled_synthetic_execution(expiry=1)
    time.sleep(1.5)
    recover_denied(data,eid,ref)


def test_recovery_cross_execution_evidence_rejected():
    data,eid,ref=reconciled_synthetic_execution()
    other,other_eid,foreign_ref=reconciled_synthetic_execution()
    recover_denied(data,eid,foreign_ref)
    with connect() as c:
        c.execute("set role service_role")
        assert c.execute("select public.generation_resume_after_reconciliation(%s,%s,%s,%s)",
                         (eid,data[0],data[2],ref)).fetchone()[0]
