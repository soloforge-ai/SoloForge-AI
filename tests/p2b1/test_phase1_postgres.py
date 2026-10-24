"""Native PostgreSQL 17 Phase 1 migration/security tests, disposable database only."""
import os
from pathlib import Path
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("P2B1_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="disposable PostgreSQL DSN missing")


@pytest.fixture(scope="module")
def conn():
    if not DSN:
        pytest.skip("no disposable database")
    with psycopg.connect(DSN, autocommit=True) as c:
        yield c


def test_six_tables_and_force_rls(conn):
    rows = conn.execute("""
      select c.relname,c.relrowsecurity,c.relforcerowsecurity
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='public' and c.relname like 'generation_%'
        and c.relkind='r'
    """).fetchall()
    assert len(rows) == 6, rows
    assert all(rls and force for _,rls,force in rows)


def test_no_client_dml_or_select(conn):
    tables = ('generation_budget_accounts','generation_approvals',
              'generation_executions','generation_requests',
              'generation_budget_ledger','generation_events')
    for role in ('anon','authenticated'):
        for table in tables:
            assert not conn.execute(
                "select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",
                (role,'public.'+table)).fetchone()[0]


def test_immutable_triggers_installed(conn):
    names = {r[0] for r in conn.execute("""
      select tgname from pg_trigger t join pg_class c on c.oid=t.tgrelid
      join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='public' and c.relname like 'generation_%' and not t.tgisinternal
    """)}
    assert {'generation_accounts_immutable','generation_approvals_immutable',
            'generation_executions_immutable','generation_requests_immutable',
            'generation_ledger_immutable','generation_events_immutable',
            'generation_approval_snapshot','generation_execution_snapshot',
            'generation_request_snapshot'} <= names


def test_no_rpc_execution_exposed_to_client(conn):
    for (oid,) in conn.execute("""
      select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='public' and p.proname like 'generation_%'
    """):
        for role in ('anon','authenticated'):
            assert not conn.execute("select has_function_privilege(%s,%s,'EXECUTE')",
                                    (role,oid)).fetchone()[0]


def test_original_four_slide_constraint(conn):
    row=conn.execute("""
      select pg_get_constraintdef(oid) from pg_constraint
      where conrelid='public.generation_requests'::regclass and contype='c'
    """).fetchall()
    assert any('slide_ordinal' in d and '4' in d for (d,) in row)
