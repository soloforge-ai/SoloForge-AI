"""Effective PostgreSQL privileges for the P2-B1 RPC-only boundary.

Uses SET ROLE against disposable PostgreSQL. No production access.
"""
import os
import pytest

psycopg = pytest.importorskip("psycopg")
pytestmark = pytest.mark.skipif(not os.getenv("P2B1_TEST_DSN"), reason="disposable DB missing")

TABLES = (
    "generation_budget_accounts", "generation_approvals",
    "generation_executions", "generation_requests",
    "generation_budget_ledger", "generation_events",
)
RPCS = (
    "generation_reserve_execution(uuid,uuid,text,text)",
    "generation_settle_execution(uuid,uuid,text,numeric,text)",
    "generation_mark_call_started(uuid,uuid,text)",
    "generation_record_verified_result(uuid,uuid,text,text,text,numeric,text,text,text,text)",
    "generation_resume_after_reconciliation(uuid,uuid,text,text)",
)

def db():
    return psycopg.connect(os.environ["P2B1_TEST_DSN"])

@pytest.mark.parametrize("role", ("anon", "authenticated", "service_role"))
def test_effective_table_dml_denied(role):
    with db() as conn:
        conn.execute("set role " + role)
        for table in TABLES:
            for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                allowed = conn.execute(
                    "select has_table_privilege(current_user,%s,%s)",
                    ("public." + table, privilege),
                ).fetchone()[0]
                assert not allowed, (role, table, privilege)
        # Even a single column-level grant can permit a direct UPDATE.
        for table in TABLES:
            columns = conn.execute(
                """select a.attname from pg_attribute a
                   join pg_class t on t.oid=a.attrelid
                   join pg_namespace n on n.oid=t.relnamespace
                   where n.nspname='public' and t.relname=%s
                     and a.attnum>0 and not a.attisdropped""", (table,)
            ).fetchall()
            for (column,) in columns:
                assert not conn.execute(
                    "select has_column_privilege(current_user,%s,%s,%s)",
                    ("public." + table, column, "UPDATE"),
                ).fetchone()[0], (role, table, column)

@pytest.mark.parametrize("role", ("anon", "authenticated"))
def test_user_roles_cannot_execute_generation_rpcs(role):
    with db() as conn:
        conn.execute("set role " + role)
        for rpc in RPCS:
            assert not conn.execute(
                "select has_function_privilege(current_user,%s,%s)",
                ("public." + rpc, "EXECUTE"),
            ).fetchone()[0], (role, rpc)

def test_service_role_has_rpc_only_and_cannot_mint_attestation():
    with db() as conn:
        conn.execute("set role service_role")
        for rpc in RPCS:
            assert conn.execute(
                "select has_function_privilege(current_user,%s,%s)",
                ("public." + rpc, "EXECUTE"),
            ).fetchone()[0], rpc
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "SELECT"):
            assert not conn.execute(
                "select has_table_privilege(current_user,%s,%s)",
                ("generation_trust.wallet_attestations", privilege),
            ).fetchone()[0], privilege

def test_rpc_definer_ownership_is_not_service_role():
    with db() as conn:
        rows = conn.execute(
            """select p.proname, r.rolname, p.prosecdef,
                      p.proconfig
               from pg_proc p join pg_namespace n on n.oid=p.pronamespace
               join pg_roles r on r.oid=p.proowner
               where n.nspname='public'
               and p.proname in (
                 'generation_reserve_execution','generation_settle_execution',
                 'generation_mark_call_started','generation_record_verified_result',
                 'generation_resume_after_reconciliation')"""
        ).fetchall()
        assert len(rows) == 5
        for name, owner, definer, config in rows:
            assert owner not in ("service_role", "anon", "authenticated"), (name, owner)
            assert definer, name
            assert config is not None and "search_path=" in config, name
