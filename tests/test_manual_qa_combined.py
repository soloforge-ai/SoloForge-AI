"""Combined owner-binding + manual QA DB integration on disposable PostgreSQL only."""
import os
import uuid
import psycopg
import pytest

DSN = os.environ["TEST_DATABASE_URL"]
OWNER = "72112ead-d399-4a40-aa51-ee17811cb10d"

def test_owner_columns_and_legacy_preserved():
    with psycopg.connect(DSN, autocommit=True) as conn:
        rows = conn.execute("SELECT owner_user_id,provider_subject FROM public.pollinations_sessions WHERE session_id='legacy'").fetchall()
        assert rows == [(None, None)]
        cols = {r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='pollinations_sessions'")}
        assert {"owner_user_id", "provider_subject"} <= cols

def test_new_unbound_session_rejected():
    with psycopg.connect(DSN, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO public.pollinations_sessions(id,session_id,access_token) VALUES (%s,%s,%s)",(str(uuid.uuid4()),"unbound-"+uuid.uuid4().hex,"synthetic-only"))

def test_bound_owner_session_and_mismatch_rejected():
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("INSERT INTO public.pollinations_sessions(id,session_id,access_token,owner_user_id,provider_subject) VALUES (%s,%s,%s,%s,%s)",(str(uuid.uuid4()),"bound-"+uuid.uuid4().hex,"synthetic-only",OWNER,"synthetic-subject"))
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO public.pollinations_sessions(id,session_id,access_token,owner_user_id) VALUES (%s,%s,%s,%s)",(str(uuid.uuid4()),"partial-"+uuid.uuid4().hex,"synthetic-only",OWNER))

def test_service_rpc_present_and_client_execute_denied():
    with psycopg.connect(DSN, autocommit=True) as conn:
        assert conn.execute("SELECT to_regprocedure('public.manual_qa_claim(uuid,text,text,text,numeric)') IS NOT NULL").fetchone()[0]
        assert conn.execute("SELECT to_regprocedure('public.manual_qa_settle(uuid,text,numeric)') IS NOT NULL").fetchone()[0]
        for role in ("anon","authenticated"):
            for fn in ("manual_qa_claim(uuid,text,text,text,numeric)","manual_qa_settle(uuid,text,numeric)"):
                assert not conn.execute("SELECT has_function_privilege(%s,%s,'EXECUTE')",(role,"public."+fn)).fetchone()[0]
