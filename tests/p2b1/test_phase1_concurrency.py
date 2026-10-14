"""Native PostgreSQL multi-connection P2-B1 tests. Disposable DB ONLY."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("P2B1_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="disposable DB missing")


def uid():
    return str(uuid.uuid4())


def connect():
    return psycopg.connect(DSN)


def seed(wallet_amount=10):
    owner, account, session, job = uid(), uid(), uid(), uid()
    with connect() as c:
        c.execute("insert into auth.users(id) values(%s)", (owner,))
        c.execute("insert into public.pollinations_sessions(session_id) values(%s)", (session,))
        c.execute("insert into public.content_jobs(id) values(%s)", (job,))
        c.execute("""insert into public.generation_budget_accounts
          (id,owner_user_id,pollinations_session_id,provider_wallet_fingerprint,
           wallet_category,owner_session_verified_at,allocation_state,allocation_ref,
           allocation_verified_at,allocated_pollen)
          values(%s,%s,%s,%s,'QUEST',now(),'ALLOCATED','synthetic-allocation',now(),%s)""",
          (account,owner,session,uuid.uuid4().hex*2,wallet_amount))
        c.execute("""insert into generation_trust.wallet_attestations
          (budget_account_id,owner_user_id,pollinations_session_id,wallet_fingerprint,
           wallet_category,authorization_ref,allocation_ref,max_authorized_pollen,
           verified_at,expires_at,evidence_sha256)
          select id,owner_user_id,pollinations_session_id,provider_wallet_fingerprint,
          wallet_category,'synthetic-provider-authority','synthetic-allocation',%s,
          now(),now()+interval '1 hour',%s
          from public.generation_budget_accounts where id=%s""",
          (wallet_amount,'d'*64,account))
    return owner,account,session,job


def approval(data,amount=7):
    owner,account,session,job=data
    aid=uid()
    snap='{"slides":[{"s":1},{"s":2},{"s":3},{"s":4}],"model_id":"synthetic","model_mapping_version":"1","dimensions":"1024x1024","storyboard_sha256":"synthetic"}'
    refs='[{"bucket":"test","object_key":"test","object_version":"v1","sha256":"'+'a'*64+'"}]'
    with connect() as c:
        c.execute("""insert into public.generation_approvals
          (id,approval_key,budget_account_id,owner_user_id,pollinations_session_id,
           content_job_id,content_job_revision,skill_id,skill_version,snapshot_digest,
           snapshot_json,reference_snapshot,request_count,max_pollen,quote_version,
           quote_expires_at,expires_at)
          values(%s,%s,%s,%s,%s,%s,'1','SALES_CAROUSEL_4_V1','1',%s,
           %s::jsonb,%s::jsonb,4,%s,'test',now()+interval '2 hours',now()+interval '1 hour')""",
          (aid,uid(),account,owner,session,job,'b'*64,snap,refs,amount))
    return aid


def reserve(data,aid,key):
    owner,_,session,_=data
    with connect() as c:
        c.execute("set role service_role")
        return c.execute("select public.generation_reserve_execution(%s,%s,%s,%s)",
                         (aid,owner,session,key)).fetchone()[0]


def test_concurrent_oversubscription():
    data=seed()
    aids=[approval(data),approval(data)]
    def worker(pair):
        try:
            return reserve(data,*pair)
        except psycopg.Error:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(worker,[(aids[0],uid()),(aids[1],uid())]))
    assert sum(v is not None for v in outcomes)==1
    with connect() as c:
        assert c.execute("select reserved_pollen from public.generation_budget_accounts where id=%s",
                         (data[1],)).fetchone()[0]==Decimal('7')


def test_reservation_replay_idempotent():
    data=seed()
    aid=approval(data,3)
    key=uid()
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:reserve(data,aid,key),range(2)))
    assert ids[0]==ids[1]
    with connect() as c:
        assert c.execute("select reserved_pollen from public.generation_budget_accounts where id=%s",
                         (data[1],)).fetchone()[0]==Decimal('3')


def test_wrong_owner_rejected():
    data=seed()
    aid=approval(data,2)
    with pytest.raises(psycopg.Error):
        reserve((uid(),data[1],data[2],data[3]),aid,uid())


def test_settlement_after_four_verified_slides():
    data=seed()
    eid=reserve(data,approval(data,5),uid())
    with connect() as c:
        rows=c.execute("""select id from public.generation_requests where execution_id=%s
          order by slide_ordinal""",(eid,)).fetchall()
        c.execute("set role service_role")
        for (rid,) in rows:
            assert c.execute("select public.generation_mark_call_started(%s,%s,%s)",
                             (rid,data[0],data[2])).fetchone()[0]
            assert c.execute("""select public.generation_record_verified_result(
              %s,%s,%s,'SUCCEEDED','synthetic-evidence',1,'test',%s,'v1',%s)""",
              (rid,data[0],data[2],str(rid),'c'*64)).fetchone()[0]
        assert c.execute("select public.generation_settle_execution(%s,%s,%s,4,'synthetic-evidence')",
                         (eid,data[0],data[2])).fetchone()[0]
        assert c.execute("select public.generation_settle_execution(%s,%s,%s,4,'synthetic-evidence')",
                         (eid,data[0],data[2])).fetchone()[0]
        c.execute("reset role")
        assert c.execute("""select reserved_pollen,spent_pollen
          from public.generation_budget_accounts where id=%s""",(data[1],)).fetchone()==(0,4)


def test_authenticated_cannot_reserve():
    data=seed()
    aid=approval(data,2)
    with connect() as c:
        c.execute("set role authenticated")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_reserve_execution(%s,%s,%s,%s)",
                      (aid,data[0],data[2],uid()))


def test_ambiguous_provider_result_fences_execution():
    data=seed()
    eid=reserve(data,approval(data,5),uid())
    with connect() as c:
        rows=c.execute("""select id from public.generation_requests where execution_id=%s
          order by slide_ordinal""",(eid,)).fetchall()
        c.execute("set role service_role")
        assert c.execute("select public.generation_mark_call_started(%s,%s,%s)",
                         (rows[0][0],data[0],data[2])).fetchone()[0]
        assert c.execute("""select public.generation_record_verified_result(
          %s,%s,%s,'UNKNOWN_RECONCILE','synthetic-uncertain',0)""",
          (rows[0][0],data[0],data[2])).fetchone()[0]
        with pytest.raises(psycopg.Error):
            with c.transaction():
                c.execute("select public.generation_mark_call_started(%s,%s,%s)",
                          (rows[1][0],data[0],data[2]))
        with pytest.raises(psycopg.Error):
            with c.transaction():
                c.execute("select public.generation_settle_execution(%s,%s,%s,0,'synthetic-uncertain')",
                          (eid,data[0],data[2]))


def test_service_role_cannot_mint_trusted_attestation():
    data=seed()
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            with c.transaction():
                c.execute("""update generation_trust.wallet_attestations
                  set expires_at=now()+interval '10 years'
                  where budget_account_id=%s""",(data[1],))


def test_missing_independent_attestation_blocks_reservation():
    data=seed()
    aid=approval(data,2)
    with connect() as c:
        c.execute("delete from generation_trust.wallet_attestations where budget_account_id=%s",(data[1],))
    with pytest.raises(psycopg.Error):
        reserve(data,aid,uid())


def test_expired_independent_attestation_blocks_reservation():
    data=seed()
    aid=approval(data,2)
    with connect() as c:
        c.execute("""update generation_trust.wallet_attestations
          set verified_at=now()-interval '2 days',expires_at=now()-interval '1 day'
          where budget_account_id=%s""",(data[1],))
    with pytest.raises(psycopg.Error):
        reserve(data,aid,uid())


def test_revoked_independent_attestation_blocks_reservation():
    data=seed()
    aid=approval(data,2)
    with connect() as c:
        c.execute("update generation_trust.wallet_attestations set revoked_at=now() where budget_account_id=%s",(data[1],))
    with pytest.raises(psycopg.Error):
        reserve(data,aid,uid())


def test_immutable_audit_and_evidence():
    data=seed()
    eid=reserve(data,approval(data,4),uid())
    with connect() as c:
        events=c.execute("""select event_type,safe_detail from public.generation_events
          where execution_id=%s order by created_at""",(eid,)).fetchall()
        assert {x[0] for x in events}>={'CLAIMED','BUDGET_RESERVED'}
        assert events[0][1]
        with pytest.raises(psycopg.Error):
            with c.transaction():
                c.execute("""update public.generation_events set safe_detail='{}'
                  where execution_id=%s""",(eid,))


def test_attestation_cannot_be_minted_with_service_role():
    data=seed()
    with connect() as c:
        c.execute("set role service_role")
        with pytest.raises(psycopg.Error):
            with c.transaction():
                c.execute("""insert into generation_trust.wallet_attestations
                  (budget_account_id,owner_user_id,pollinations_session_id,wallet_fingerprint,
                   wallet_category,authorization_ref,allocation_ref,max_authorized_pollen,
                   verified_at,expires_at,evidence_sha256)
                  select id,owner_user_id,pollinations_session_id,provider_wallet_fingerprint,
                  wallet_category,'forged','forged',1,now(),now()+interval '1 day',%s
                  from public.generation_budget_accounts where id=%s""",
                  ('f'*64,data[1]))
