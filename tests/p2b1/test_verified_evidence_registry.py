"""Isolated evidence registry denies application roles (disposable PostgreSQL only)."""
import os
import pytest
psycopg=pytest.importorskip("psycopg")
pytestmark=pytest.mark.skipif(not os.getenv("P2B1_TEST_DSN"),reason="disposable DB missing")
@pytest.mark.parametrize("role",["anon","authenticated","service_role"])
def test_no_application_role_can_mint_or_modify_verified_evidence(role):
    with psycopg.connect(os.environ["P2B1_TEST_DSN"]) as c:
        c.execute("set role "+role)
        for privilege in ("SELECT","INSERT","UPDATE","DELETE","TRUNCATE"):
            assert not c.execute("select has_table_privilege(current_user,%s,%s)",
                ("generation_evidence.verified_results",privilege)).fetchone()[0]
        assert not c.execute("select has_function_privilege(current_user,%s,%s)",
            ("generation_evidence.check_result(uuid,uuid,uuid,text,text,text,numeric)","EXECUTE")).fetchone()[0]
def test_verified_evidence_table_is_force_rls_and_immutable():
    with psycopg.connect(os.environ["P2B1_TEST_DSN"]) as c:
        assert c.execute("""select relrowsecurity and relforcerowsecurity from pg_class
          where oid='generation_evidence.verified_results'::regclass""").fetchone()[0]
        assert c.execute("""select count(*) from pg_trigger
          where tgrelid='generation_evidence.verified_results'::regclass
            and not tgisinternal and tgname='verified_results_immutable'""").fetchone()[0]==1
