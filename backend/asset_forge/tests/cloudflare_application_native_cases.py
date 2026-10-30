"""Reuse application HTTP contracts on disposable PG17, with real app AES-GCM.

Private image storage is the retained in-memory fixture, not Supabase/RLS proof.
Database calls use independent native connections; no PGlite is used here.
"""
import ast
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from uuid import uuid4
import pytest
import test_cloudflare_application as application
import test_cloudflare_persistence as persistence
from test_cloudflare_application import (
    app, persistent, prepare, authorize, PRINCIPAL,
    test_owner_http_vertical_slice_to_existing_review_and_revoke,
    test_non_owner_cannot_submit_or_execute,
    test_pending_revoked_budget_model_and_unit_denial,
    test_timeout_is_sanitized_no_replay_and_reservation_held,
    test_default_app_has_no_cloudflare_capability,
    test_cross_principal_missing_consent_immutable_job_and_review_reject,
    test_failed_asset_persistence_is_unknown_without_replay,
    test_concurrent_http_execution_has_one_dispatch,
)
from cloudflare_native_cases import AppCrypto
from cloudflare_native_fixture import disposable_database, connection
from test_cloudflare_http import (
    test_owner_http_transport_to_private_review_and_retained_export,
    test_http_failure_unknown_held_no_replay_no_secret,
    test_live_transport_default_flags_and_redirects_fail_closed,
    test_exact_credential_a_dispatch_and_revoked_denial,
    test_revoked_credential_denies_http_dispatch,
    test_invalid_http_contract_never_opens_socket,
    test_http_flow_requires_consent_budget_and_owner,
    test_live_mode_request_is_immutable_and_unverified_prices_deny,
)


@pytest.fixture(scope='module')
def byop_db():
    root = Path(__file__).resolve().parents[1]
    source = ast.parse(Path(__file__).with_name('test_byop_repository.py').read_text())
    full_jobs = next(n.value for n in ast.walk(source) if isinstance(n, ast.Constant)
        and isinstance(n.value, str) and 'create table public.content_jobs (' in n.value)
    schema = persistence.sanitized_schema().replace(
        'create table public.content_jobs(id uuid primary key,script text,content_package jsonb);', full_jobs)
    schema += (root/'sql/byop_owner_pilot_candidate.sql').read_text()
    schema += (root/'sql/byop_cloudflare_application_candidate.sql').read_text()
    with disposable_database(schema) as holder:
        yield holder['db']


@pytest.fixture(scope='module')
def application_db(byop_db):
    return byop_db


@pytest.fixture(autouse=True)
def app_crypto(monkeypatch):
    import sys, cryptography
    assert sys.version_info[:2] == (3, 12)
    assert cryptography.__version__ == '46.0.3'
    monkeypatch.setattr(application, 'ExistingSystemCrypto', AppCrypto)


def test_native_application_rls_and_rpc_permissions(app):
    db = app['db']
    cid, jid = prepare(app)
    for role in ('anon', 'authenticated'):
        for sql, params in (
            ('select public.byop_cloudflare_credentials($1)', [PRINCIPAL]),
            ('select public.byop_cloudflare_job($1,$2,$3)', [PRINCIPAL, 'cat', application.MODEL]),
        ):
            with pytest.raises(RuntimeError): db.query(sql, params, role)
    for table in ('content_jobs', 'pollinations_sessions', 'byop_ledgers'):
        assert db.query('select relrowsecurity from pg_class where oid=$1::regclass',
            ['public.'+table])[0]['relrowsecurity'] is True
        db.query('grant select on public.'+table+' to anon,authenticated')
        try:
            for role in ('anon', 'authenticated'):
                assert db.query('select * from public.'+table, role=role) == []
        finally:
            db.query('revoke select on public.'+table+' from anon,authenticated')
    assert app['http']('GET', f'/jobs/{jid}').status_code == 200


def test_native_application_revocation_commits_before_claim(app):
    cid, jid = prepare(app)
    consent = authorize(app, cid, jid).json()
    eid = str(uuid4())
    ready, proceed = Event(), Event()
    original = app['ledger'].store.offline_transport
    def intercepted(method, path, body=None, **kwargs):
        if path == 'rpc/byop_cloudflare_claim':
            ready.set()
            assert proceed.wait(10)
        return original(method, path, body, **kwargs)
    app['ledger'].store.offline_transport = intercepted
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(app['http'], 'POST', '/executions',
            json={'consent_id':consent['consent_id'], 'execution_id':eid})
        assert ready.wait(10)
        with connection(app['db'].name) as conn:
            conn.execute('select id from public.pollinations_sessions where id=%s for update', (cid,))
            conn.execute('update public.pollinations_sessions set byop_revoked_at=clock_timestamp() where id=%s', (cid,))
            proceed.set()
            deadline = time.monotonic()+5
            while True:
                conn.execute('select pg_stat_clear_snapshot()')
                blocked = conn.execute("select count(*) from pg_stat_activity where datname=%s and pid<>pg_backend_pid() and wait_event_type='Lock' and position('byop_cloudflare_claim' in query)>0", (app['db'].name,)).fetchone()[0]
                if blocked: break
                assert time.monotonic() < deadline
                time.sleep(.05)
        assert future.result(20).status_code in (409, 503)
    assert not app['calls']
    state = app['ledger'].store.read(PRINCIPAL)[1]['executions'][eid]
    assert state['state'] == 'RESERVED' and state['reserved'] == 70
    assert app['http']('GET', f'/jobs/{jid}').json()['status'] == 'ASSET_QUEUED'
