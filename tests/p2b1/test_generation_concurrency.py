"""P2-B1 multi-connection integration tests.

Run ONLY against an isolated Supabase/Postgres test database with migrations applied.
P2B1_TEST_DSN must be an isolated test DSN; this suite never uses production credentials.
Requires psycopg >=3 and pytest. No external provider calls.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("P2B1_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="isolated P2B1_TEST_DSN required")


def new_id():
    return str(uuid.uuid4())


def connect():
    return psycopg.connect(DSN, autocommit=False)


def service(conn):
    # Emulates Supabase JWT claim only on a disposable DB; not a production auth proof.
    conn.execute("select set_config('request.jwt.claim.role','service_role',true)")
    conn.execute("select set_config('request.jwt.claims','{\"role\":\"service_role\"}',true)")


@pytest.fixture
def seeded():
    owner, budget, approval, execution = (new_id() for _ in range(4))
    requests = [new_id(), new_id()]
    with connect() as c:
        service(c)
        c.execute("""insert into public.generation_budget_accounts
          (id,owner_user_id,provider_subject,wallet_allocation_pollen,enabled)
          values (%s,%s,'verified-test-subject',10,true)""", (budget, owner))
        c.execute("""insert into public.generation_approvals
          (id,budget_account_id,owner_user_id,approved_models,max_pollen,expires_at,approval_snapshot)
          values (%s,%s,%s,ARRAY['test-model'],10,now()+interval '1 hour','{}')""",
          (approval,budget,owner))
        c.execute("""insert into public.generation_executions
          (id,approval_id,budget_account_id,owner_user_id,idempotency_key,execution_snapshot,state)
          values (%s,%s,%s,%s,%s,'{}','APPROVED')""",
          (execution,approval,budget,owner,new_id()))
        for i, rid in enumerate(requests):
            c.execute("""insert into public.generation_requests
              (id,execution_id,slide_index,model_id,request_snapshot)
              values (%s,%s,%s,'test-model','{}')""", (rid,execution,i))
    yield owner,budget,execution,requests
    with connect() as c:
        # Explicit test-only cleanup; only rows created by this fixture.
        c.execute("delete from public.generation_events where execution_id=%s",(execution,))
        c.execute("delete from public.generation_budget_ledger where execution_id=%s",(execution,))
        c.execute("delete from public.generation_requests where execution_id=%s",(execution,))
        c.execute("delete from public.generation_executions where id=%s",(execution,))
        c.execute("delete from public.generation_approvals where id=%s",(approval,))
        c.execute("delete from public.generation_budget_accounts where id=%s",(budget,))


def reserve(execution,request,amount,key):
    try:
        with connect() as c:
            service(c)
            return c.execute("select public.generation_reserve_budget(%s,%s,%s,%s)",
                             (execution,request,amount,key)).fetchone()[0]
    except psycopg.Error:
        return None


def test_parallel_reservation_never_exceeds_wallet(seeded):
    owner,budget,execution,requests=seeded
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda a: reserve(execution,a[0],Decimal("7"),new_id()), requests))
    assert sum(v is not None for v in results)==1
    with connect() as c:
        reserved,spent=c.execute("""select reserved_pollen,spent_pollen
          from public.generation_budget_accounts where id=%s""",(budget,)).fetchone()
        assert reserved==Decimal("7")
        assert spent==0


def test_duplicate_reservation_idempotent(seeded):
    owner,budget,execution,requests=seeded
    key=new_id()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:reserve(execution,requests[0],Decimal("3"),key),range(2)))
    assert results[0] is not None and results[0]==results[1]
    with connect() as c:
        (reserved,)=c.execute("""select reserved_pollen from public.generation_budget_accounts
          where id=%s""",(budget,)).fetchone()
        assert reserved==Decimal("3")


def test_wrong_owner_cannot_claim(seeded):
    _,_,_,requests=seeded
    with connect() as c:
        service(c)
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_claim_request(%s,%s)",(requests[0],new_id()))


def test_untrusted_role_cannot_reserve(seeded):
    _,_,execution,requests=seeded
    with connect() as c:
        c.execute("select set_config('request.jwt.claim.role','authenticated',true)")
        with pytest.raises(psycopg.Error):
            c.execute("select public.generation_reserve_budget(%s,%s,1,%s)",
                      (execution,requests[0],new_id()))
