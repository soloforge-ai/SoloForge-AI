"""Offline migration rehearsal: PostgreSQL/WASM, NOT native PG/PostgREST proof."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest
from test_owner_v2 import Database

ROOT = Path(__file__).resolve().parents[3]
SQL = ROOT / 'backend/asset_forge/sql/pollinations_login_release_candidate.sql'

@pytest.fixture
def legacy_db():
    # Reuse the existing sanitized legacy schema fixture, never production rows.
    tree = ast.parse(Path(__file__).with_name('test_pollinations_owner_binding.py').read_text())
    legacy = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                  and isinstance(n.value, str) and 'create schema auth;' in n.value)
    schema = (ROOT / 'supabase/migrations/20261024151629_owner_identity_v2.sql').read_text() + legacy
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql') as snapshot:
        snapshot.write(schema); snapshot.flush()
        process = subprocess.Popen(['node', str(Path(__file__).with_name('owner_v2_pg_bridge.mjs')), snapshot.name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        assert json.loads(process.stdout.readline()) == {'ready': True}
        db = Database(process)
        try:
            yield db
        finally:
            process.stdin.close()
            assert process.wait(timeout=15) == 0

def ddl(db, sql):
    with db.lock:
        db.process.stdin.write(json.dumps({'sql': sql, 'exec': True}) + '\n')
        db.process.stdin.flush()
        result = json.loads(db.process.stdout.readline())
    if 'error' in result:
        raise RuntimeError(result['error'])


def seed(db, session='legacy'):
    db.query("insert into public.pollinations_sessions(session_id,access_token,owner_user_id,provider_subject,expires_at) values ($1,'sk_OFFLINE_FIXTURE_ONLY','33333333-3333-4333-8333-333333333333','offline-subject',now()+interval '1 hour')", [session])

def test_preserves_legacy_and_denies_spending_and_client_access(legacy_db):
    db = legacy_db
    seed(db)
    before = db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions')
    ddl(db, SQL.read_text())
    assert db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions') == before
    row = db.query('select submitted_by_owner,verification_status,provider_ownership_verified,spending_authorized,length(credential_digest) as digest_length from public.pollinations_sessions')[0]
    assert row == dict(submitted_by_owner=None, verification_status='PENDING_VERIFICATION', provider_ownership_verified=False, spending_authorized=False, digest_length=64)
    for role in ('anon','authenticated'):
        with pytest.raises(RuntimeError):
            db.query('select * from public.pollinations_sessions', role=role)
    with pytest.raises(RuntimeError):
        db.query('update public.pollinations_sessions set spending_authorized=true')
    with pytest.raises(RuntimeError):
        ddl(db, SQL.read_text())
    ddl(db, 'rollback')
    assert db.query('select count(*) as n from public.pollinations_sessions')[0]['n'] == 1

def test_duplicate_preflight_rolls_back_without_row_loss(legacy_db):
    db = legacy_db
    seed(db, 'a'); seed(db, 'b')
    with pytest.raises(RuntimeError, match='Duplicate credentials'):
        ddl(db, SQL.read_text())
    ddl(db, 'rollback')
    assert db.query('select count(*) as n from public.pollinations_sessions')[0]['n'] == 2
    assert db.query("select count(*) as n from information_schema.columns where table_name='pollinations_sessions' and column_name='submitted_by_owner'")[0]['n'] == 0

def test_release_template_is_pinned_manual_and_execution_disabled():
    config = json.loads((ROOT / 'docs/POLLINATIONS_LOGIN_RELEASE.template.json').read_text())
    assert config['source_sha'] == 'a04a2ede7c9de94a0f523ee8e9e1a7d51b771f1b'
    assert config['web']['autoDeploy'] is config['backend']['autoDeploy'] is False
    assert '--dart-define=SOLOFORGE_OWNER_V2=true' in config['web']['build']
    settings = config['backend']['proposed_nonsecret_settings']
    assert settings['SOLOFORGE_RUN_EMBEDDED_WORKERS'] == settings['SOLOFORGE_RUN_DEDICATED_WORKERS'] == 'false'
    assert 'POLLINATIONS_API_KEY' not in settings
