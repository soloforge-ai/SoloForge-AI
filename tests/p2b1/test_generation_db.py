"""Native PostgreSQL P2-B1 security/concurrency checks. Requires disposable database.
Run: P2B1_TEST_DSN=postgresql://... pytest -q tests/p2b1/test_generation_db.py
Do NOT point this at production. psycopg[binary] and pytest required.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("P2B1_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="disposable P2B1_TEST_DSN not set")
ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = [
    ROOT / "supabase/migrations/202610140001_generation_db_foundation.sql",
    ROOT / "supabase/migrations/202610140002_generation_service_rpcs.sql",
]


@pytest.fixture(scope="module")
def db():
    if not DSN:
        pytest.skip("no disposable PostgreSQL configured")
    with psycopg.connect(DSN, autocommit=True) as conn:
        # Disposable DB only. Supabase roles/auth functions must already be installed.
        for migration in MIGRATIONS:
            conn.execute(migration.read_text())
        yield conn


def test_default_wallet_disabled(db):
    with db.cursor() as cur:
        cur.execute("select enabled from public.generation_budget_accounts limit 1")
        # Foundation must never default to live execution.
        cur.execute("""
            select column_default from information_schema.columns
            where table_schema='public' and table_name='generation_budget_accounts'
              and column_name='enabled'
        """)
        assert cur.fetchone()[0] == "false"


def test_client_roles_no_rpc_execute(db):
    with db.cursor() as cur:
        cur.execute("""
            select has_function_privilege('authenticated',
             'public.generation_reserve_budget(uuid,uuid,numeric,text)', 'EXECUTE'),
             has_function_privilege('anon',
             'public.generation_claim_request(uuid,uuid)', 'EXECUTE')
        """)
        assert cur.fetchone() == (False, False)


def test_direct_client_dml_denied(db):
    with db.cursor() as cur:
        cur.execute("""
            select has_table_privilege('authenticated','public.generation_budget_ledger','INSERT'),
                   has_table_privilege('anon','public.generation_requests','UPDATE')
        """)
        assert cur.fetchone() == (False, False)


def test_concurrency_contract_requires_disposable_seed_and_service_jwt(db):
    # This is deliberately xfail until a full Supabase local role/JWT fixture is
    # provided. A direct superuser connection cannot prove service-role auth.
    pytest.xfail("native multi-connection service JWT fixture and seeded wallet required")
