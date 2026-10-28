"""Offline HTTP + actual PostgreSQL/WASM tests. No live identity or provider calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit, unquote
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.asset_forge.backend import owner_v2 as owner
from backend.asset_forge.backend import soloforge_session as first_party
from backend.asset_forge.backend import pollinations_oauth_router as routes
from backend.pollinations_sk_lifecycle import verify_identity
from test_owner_v2 import Database

ROOT = Path(__file__).resolve().parents[3]
OWNER = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'
SUBJECT = 'independently-confirmed-provider-account'
GITHUB = '33333333-3333-4333-8333-333333333333'


@pytest.fixture(scope='module')
def binding_db():
    module = os.environ.get('OWNER_V2_TEST_PGLITE')
    assert module and Path(module).is_file(), 'PGlite required; never skip SQL evidence'
    migration = ROOT / 'supabase/migrations/20261024151629_owner_identity_v2.sql'
    schema = migration.read_text() + """
        create schema auth;
        create table auth.users(id uuid primary key);
        insert into auth.users values ('33333333-3333-4333-8333-333333333333'),('22222222-2222-4222-8222-222222222222');
        create table public.pollinations_sessions(
            id uuid primary key default gen_random_uuid(), session_id text unique not null,
            access_token text not null, refresh_token text, token_type text, scope text,
            owner_user_id uuid references auth.users(id), provider_subject text,
            expires_at timestamptz, created_at timestamptz not null default now(),
            updated_at timestamptz not null default now(),
            constraint pollinations_sessions_owner_subject_together check (
                (owner_user_id is null and provider_subject is null) or
                (owner_user_id is not null and provider_subject is not null and length(btrim(provider_subject))>0)));
        create function public.reject_unbound_pollinations_session_insert() returns trigger
        language plpgsql set search_path='' as $$ begin
            if new.owner_user_id is null or new.provider_subject is null or length(btrim(new.provider_subject))=0 then
                raise check_violation using message='New Pollinations sessions require owner and provider subject';
            end if;
            return new;
        end; $$;
        create trigger pollinations_sessions_require_owner_on_insert before insert on public.pollinations_sessions
            for each row execute function public.reject_unbound_pollinations_session_insert();
    """ + (ROOT / 'backend/asset_forge/sql/pollinations_owner_binding.sql').read_text() + (ROOT / 'backend/asset_forge/sql/owner_v2_github_session_reference.sql').read_text()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql') as snapshot:
        snapshot.write(schema); snapshot.flush()
        process = subprocess.Popen(['node', str(Path(__file__).with_name('owner_v2_pg_bridge.mjs')), snapshot.name],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        assert json.loads(process.stdout.readline()) == {'ready': True}
        db = Database(process)
        yield db
        process.stdin.close()
        assert process.wait(timeout=15) == 0


@pytest.fixture
def flow(binding_db, monkeypatch):
    db = binding_db
    db.query('truncate public.pollinations_sessions, public.owner_v2_sessions, public.owner_v2_challenges, public.soloforge_owner_accounts, public.soloforge_owners')
    db.query('select public.owner_v2_bootstrap($1,$2)', [OWNER, 'owner@example.test'])
    db.query('''update public.soloforge_owner_accounts set provider_account_id=$1,
        verification_status='verified', verification_evidence='independent administrative fixture', verified_at=now()
        where provider='supabase' ''', [GITHUB])
    db.query('''update public.soloforge_owner_accounts set provider_account_id=$1,
        verification_status='verified', verification_evidence='independent provider fixture', verified_at=now()
        where provider='pollinations' ''', [SUBJECT])
    monkeypatch.setenv('OWNER_V2_GITHUB_ENABLED', 'true')
    monkeypatch.setenv('POLLINATIONS_CLIENT_ID', 'offline-client')
    monkeypatch.setenv('POLLINATIONS_REDIRECT_URI', 'https://testserver/auth/pollinations/callback')
    monkeypatch.setattr(first_party, '_supabase_owner_id', lambda authorization: GITHUB if authorization == 'Bearer github-proof' else None)
    monkeypatch.setattr(owner, 'rpc', db.call)
    class SQLBackedOwner(owner.OwnerV2):
        def __init__(self):
            super().__init__(call=db.call)
    monkeypatch.setattr(owner, 'OwnerV2', SQLBackedOwner)
    monkeypatch.setattr(routes, '_supabase_config', lambda: ('https://offline.invalid', 'fake'))
    calls = []

    def transport(method, path, *, body=None, prefer=None):
        calls.append((method, path))
        if path == 'rpc/pollinations_reverify':
            result = db.query('select public.pollinations_reverify($1,$2,$3,$4) as value',
                [body['p_owner_id'], body['p_record_id'], body['p_subject'], body['p_identity_verified']], 'service_role')[0]['value']
            return json.dumps(result).encode()
        table, _, query = path.partition('?')
        assert table in ('pollinations_sessions', 'soloforge_owner_accounts')
        filters, params = [], []
        for key, values in parse_qs(query).items():
            if key in ('select', 'limit', 'order', 'on_conflict'):
                continue
            assert key in ('id', 'session_id', 'submitted_by_owner', 'provider', 'owner_id', 'verification_status', 'expires_at', 'owner_user_id')
            value = values[0]
            if value == 'is.null':
                filters.append(f'{key} is null')
            else:
                op, value = value.split('.', 1)
                assert op in ('eq', 'gt')
                params.append(value)
                filters.append(f'{key} {"=" if op == "eq" else ">"} ${len(params)}')
        where = ' where ' + ' and '.join(filters) if filters else ''
        if method == 'GET':
            select = parse_qs(query).get('select', ['*'])[0]
            assert all(c.isalnum() or c in '_,' for c in select) or select == '*'
            rows = db.query(f'select {select} from public.{table}' + where, params, 'service_role')
        elif method == 'POST':
            columns = list(body)
            rows = db.query(f'insert into public.{table} (' + ','.join(columns) + ') values ('
                + ','.join(f'${i}' for i in range(1, len(columns)+1)) + ') returning *', list(body.values()), 'service_role')
        elif method == 'PATCH':
            assignments = []
            for k, value in body.items():
                assert k in ('verification_status', 'provider_subject', 'submitted_by_owner', 'provider_ownership_verified', 'spending_authorized')
                params.append(value)
                assignments.append(f'{k}=${len(params)}')
            rows = db.query(f'update public.{table} set ' + ','.join(assignments) + where + ' returning *', params, 'service_role')
        elif method == 'DELETE':
            rows = db.query(f'delete from public.{table}' + where + ' returning id', params, 'service_role')
        else:
            raise AssertionError(method)
        return json.dumps(rows).encode()

    monkeypatch.setattr(routes, '_supabase_request', transport)
    monkeypatch.setattr(routes, 'exchange_authorization_code', lambda *a, **k: {
        'access_token': 'sk_offline_only', 'expires_in': 600, 'scope': 'profile usage'})
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', lambda token: (200, {'sub': SUBJECT}))
    monkeypatch.setattr('backend.pollinations_sk_lifecycle.provider_get', lambda url, token: (200, {'sub': SUBJECT}) if url.endswith('userinfo') else (200, {'balance': 5}))
    routes._sessions.clear(); routes._transactions.clear(); routes._handoffs.clear(); routes._launches.clear()
    app = FastAPI(); app.include_router(first_party.router); app.include_router(routes.router)
    with TestClient(app, base_url='https://testserver') as client:
        login = client.post('/auth/soloforge/bootstrap-v2', headers={'Authorization': 'Bearer github-proof'})
        assert login.status_code == 200, login.text
        headers = {'Authorization': 'Bearer ' + login.json()['session_token']}
        yield client, headers, db, calls


def connected(flow):
    client, headers, db, calls = flow
    start = client.post('/auth/pollinations/connect', headers=headers,
        json={'client': 'mobile', 'return_to': 'soloforge://oauth/pollinations'})
    assert start.status_code == 200, start.text
    launch = client.get(start.json()['launch_path'], follow_redirects=False)
    assert launch.status_code == 302
    state = parse_qs(urlsplit(launch.headers['location']).query)['state'][0]
    callback = client.get('/auth/pollinations/callback', params={'code': 'provider-code', 'state': state}, follow_redirects=False)
    assert callback.status_code == 302, callback.text
    handoff = parse_qs(urlsplit(callback.headers['location']).query)['code'][0]
    exchanged = client.post('/auth/pollinations/mobile/exchange', headers=headers, json={'code': handoff})
    assert exchanged.status_code == 200, exchanged.text
    records = client.get('/auth/pollinations/account/credentials', headers=headers)
    assert records.status_code == 200
    return records.json()['credentials'][0]['id'], exchanged.json()['session_token'], state


def test_full_github_pending_identity_verified_inspection_no_spending(flow):
    client, headers, db, calls = flow
    record, session, state = connected(flow)
    row = db.query('select * from public.pollinations_sessions')[0]
    assert row['submitted_by_owner'] == OWNER
    assert row['verification_status'] == 'PENDING_VERIFICATION'
    pending = client.get('/auth/pollinations/sk/preflight', headers={**headers, 'X-Pollinations-Session': session})
    assert pending.status_code == 200 and pending.json()['provider_ownership_verified'] is True
    assert db.query('select verification_status from public.pollinations_sessions')[0]['verification_status'] == 'PENDING_VERIFICATION'
    verified = client.post('/auth/pollinations/sk/reverify', headers=headers, json={'credential_record_id': record})
    assert verified.status_code == 200, verified.text
    assert verified.json()['verification_status'] == 'VERIFIED'
    assert verified.json()['verification_outcome'] == 'VERIFIED'
    inspected = client.get('/auth/pollinations/account/inspect', headers=headers, params={'credential_record_id': record})
    assert inspected.status_code == 200
    assert inspected.json()['spending_authorized'] is False
    assert inspected.json()['owner_binding'] == 'VERIFIED'
    assert 'sk_offline' not in inspected.text
    assert 'sk_offline' not in client.get('/auth/pollinations/account/credentials', headers=headers).text
    assert routes.get_pollinations_access_token(session) is None
    assert db.query('select spending_authorized from public.pollinations_sessions')[0]['spending_authorized'] is False
    # Registry revocation is checked again on each protected request.
    db.query('update public.owner_v2_sessions set revoked_at=now()')
    assert client.get('/auth/pollinations/account/credentials', headers=headers).status_code == 401


@pytest.mark.parametrize('status,payload,expected', [(401, {}, SUBJECT), (403, {}, SUBJECT), (0, {}, SUBJECT),
    (500, {}, SUBJECT), (200, {}, SUBJECT), (200, {'sub':'wrong'}, SUBJECT), (200, {'sub':SUBJECT}, None),
    (200, {'sub':None}, SUBJECT), (200, {'sub':'sk_secret'}, SUBJECT)])
def test_invalid_or_unavailable_evidence_never_promotes(status, payload, expected, monkeypatch):
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', lambda token: (status, payload))
    result = verify_identity('sk_offline', 9999999999, expected)
    assert result['verification_status'] == 'PENDING_VERIFICATION'
    assert result['provider_ownership_verified'] is False
    assert result['spending_authorized'] is False
    assert result['verification_outcome'] in ('REJECTED', 'UNKNOWN')


def test_mismatch_demotes_previous_verification(flow, monkeypatch):
    client, headers, db, calls = flow
    record, session, state = connected(flow)
    assert client.post('/auth/pollinations/sk/reverify', headers=headers, json={'credential_record_id':record}).json()['verification_status'] == 'VERIFIED'
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', lambda token: (200, {'sub':'wrong'}))
    result = client.post('/auth/pollinations/sk/reverify', headers=headers, json={'credential_record_id':record})
    assert result.status_code == 200
    assert result.json()['verification_outcome'] == 'REJECTED'
    assert db.query('select provider_ownership_verified from public.pollinations_sessions')[0]['provider_ownership_verified'] is False


def test_owner_scoping_and_record_id_cannot_authorize(flow):
    client, headers, db, calls = flow
    record, session, state = connected(flow)
    assert client.get('/auth/pollinations/account/credentials').status_code == 401
    # Simulate an unrelated owner row using FK-disabled fixture only via owner isolation at API level.
    db.query('delete from public.pollinations_sessions')
    legacy(db, 'sk_unbound', record, session)
    routes._sessions.clear()
    assert client.get('/auth/pollinations/account/credentials', headers=headers).json()['credentials'] == []
    assert client.get('/auth/pollinations/account/inspect', headers=headers, params={'credential_record_id':record}).status_code == 404
    assert client.get('/auth/pollinations/account/inspect', headers={**headers,'X-Pollinations-Session':session}).status_code == 404
    assert client.post('/auth/pollinations/sk/reverify', headers=headers, json={'credential_record_id':record}).status_code == 404
    assert client.post('/auth/pollinations/logout', headers={**headers,'X-Pollinations-Session':session}).status_code == 404
    assert client.get('/auth/pollinations/account/inspect', headers={'Authorization':'Bearer '+session}, params={'credential_record_id':record}).status_code == 401


def test_state_mismatch_callback_replay_and_exchange_failure(flow, monkeypatch):
    client, headers, db, calls = flow
    record, session, state = connected(flow)
    assert client.get('/auth/pollinations/callback', params={'code':'again','state':state}, follow_redirects=False).status_code == 400
    start = client.get('/auth/pollinations/login', headers=headers, follow_redirects=False)
    state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    assert client.get('/auth/pollinations/callback', params={'code':'code','state':'wrong'}, follow_redirects=False).status_code == 400
    def fail(*a, **k): raise RuntimeError('ambiguous provider failure')
    monkeypatch.setattr(routes,'exchange_authorization_code', fail)
    assert client.get('/auth/pollinations/callback', params={'code':'code','state':state}, follow_redirects=False).status_code == 502
    assert client.get('/auth/pollinations/callback', params={'code':'code','state':state}, follow_redirects=False).status_code == 400
    assert len(db.query('select * from public.pollinations_sessions')) == 1


def legacy(db, token='sk_legacy', record_id=None, session_id=None):
    # Disposable DB only: reproduce records inserted before the production guard existed.
    db.query('alter table public.pollinations_sessions disable trigger pollinations_sessions_require_owner_on_insert')
    try:
        return db.query("insert into public.pollinations_sessions(id,session_id,access_token,expires_at) values($1,$2,$3,now()+interval '1 hour') returning id",
            [record_id or str(uuid4()),session_id or str(uuid4()),token])[0]['id']
    finally:
        db.query('alter table public.pollinations_sessions enable trigger pollinations_sessions_require_owner_on_insert')


def test_legacy_claim_requires_secret_and_matching_evidence_can_later_verify(flow):
    client, headers, db, calls = flow
    record = legacy(db)
    assert client.get('/auth/pollinations/account/credentials',headers=headers).json()['credentials'] == []
    bad = client.post('/auth/pollinations/sk/claim',headers=headers,json={'credential_record_id':record,'access_token':'sk_wrong'})
    assert bad.status_code == 404
    assert db.query('select submitted_by_owner from public.pollinations_sessions')[0]['submitted_by_owner'] is None
    good = client.post('/auth/pollinations/sk/claim',headers=headers,json={'credential_record_id':record,'access_token':'sk_legacy'})
    assert good.status_code == 200, good.text
    assert good.json()['verification_status'] == 'PENDING_VERIFICATION'
    assert client.post('/auth/pollinations/sk/claim',headers=headers,json={'credential_record_id':record,'access_token':'sk_legacy'}).status_code == 404
    verified = client.post('/auth/pollinations/sk/reverify', headers=headers,json={'credential_record_id':record})
    assert verified.json()['provider_ownership_verified'] is True


@pytest.mark.parametrize('baseline', [False, True])
def test_claim_enters_pending_before_independent_evidence_and_never_promotes(flow, monkeypatch, baseline):
    client, headers, db, calls = flow
    record = legacy(db)
    if not baseline:
        db.query("update public.soloforge_owner_accounts set verification_status='pending',verified_at=null where provider='pollinations'")
    def no_provider_call(token):
        pytest.fail('Pending admission must not call the provider')
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', no_provider_call)
    result = client.post('/auth/pollinations/sk/claim', headers=headers,
        json={'credential_record_id': record, 'access_token': 'sk_legacy'})
    assert result.status_code == 200, result.text
    assert result.json() == {'verification_status': 'PENDING_VERIFICATION',
        'provider_ownership_verified': False, 'spending_authorized': False}
    assert db.query('select submitted_by_owner from public.pollinations_sessions')[0]['submitted_by_owner'] == OWNER
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', lambda token: (200, {'sub': 'wrong' if baseline else SUBJECT}))
    checked = client.post('/auth/pollinations/sk/reverify', headers=headers,
        json={'credential_record_id': record})
    assert checked.status_code == 200, checked.text
    assert checked.json()['verification_outcome'] == ('REJECTED' if baseline else 'UNKNOWN')
    assert checked.json()['provider_ownership_verified'] is False
    assert checked.json()['spending_authorized'] is False
    row = db.query('select verification_status,provider_ownership_verified,spending_authorized from public.pollinations_sessions')[0]
    assert row == {'verification_status': 'PENDING_VERIFICATION',
        'provider_ownership_verified': False, 'spending_authorized': False}


def test_claim_requires_owner_and_cannot_hijack_verified_credential(flow, monkeypatch):
    client, headers, db, calls = flow
    record = legacy(db)
    payload = {'credential_record_id': record, 'access_token': 'sk_legacy'}
    assert client.post('/auth/pollinations/sk/claim', json=payload).status_code == 401
    assert client.post('/auth/pollinations/sk/claim', headers={'Authorization': 'Bearer '+record}, json=payload).status_code == 401
    assert client.post('/auth/pollinations/sk/claim', headers=headers, json=payload).status_code == 200
    assert client.post('/auth/pollinations/sk/reverify', headers=headers,
        json={'credential_record_id': record}).json()['verification_status'] == 'VERIFIED'
    before = db.query('select * from public.pollinations_sessions')
    assert client.post('/auth/pollinations/sk/claim', headers=headers, json=payload).status_code == 404
    assert db.query('select * from public.pollinations_sessions') == before
    # A separately authenticated owner must not adopt an already bound record, even with its SK.
    monkeypatch.setattr(routes, '_owner', lambda authorization: OTHER)
    assert client.post('/auth/pollinations/sk/claim', headers=headers, json=payload).status_code == 404
    assert db.query('select * from public.pollinations_sessions') == before


@pytest.mark.parametrize('response', [b'', b'[]', b'[{}]', b'[{},{}]', b'null', b'not-json'])
def test_ambiguous_claim_write_fails_closed_without_retry(flow, monkeypatch, response):
    client, headers, db, calls = flow
    record = legacy(db)
    original = routes._supabase_request
    writes = []
    def ambiguous(method, path, **kwargs):
        if method == 'PATCH':
            writes.append(path)
            return response
        return original(method, path, **kwargs)
    monkeypatch.setattr(routes, '_supabase_request', ambiguous)
    result = client.post('/auth/pollinations/sk/claim', headers=headers,
        json={'credential_record_id': record, 'access_token': 'sk_legacy'})
    assert result.status_code == 409
    assert len(writes) == 1
    assert db.query('select submitted_by_owner,spending_authorized from public.pollinations_sessions')[0] == {
        'submitted_by_owner': None, 'spending_authorized': False}


def test_sql_permissions_spending_and_unique_credentials(flow):
    client, headers, db, calls = flow
    legacy(db)
    for role in ('anon','authenticated'):
        with pytest.raises(RuntimeError): db.query('select * from public.pollinations_sessions',role=role)
        with pytest.raises(RuntimeError): db.query('select public.owner_v2_github_session($1,$2)',[GITHUB,'a'*64],role=role)
    with pytest.raises(RuntimeError): legacy(db)
    with pytest.raises(RuntimeError): db.query('update public.pollinations_sessions set spending_authorized=true')
    with pytest.raises(RuntimeError): db.query("update public.pollinations_sessions set access_token='sk_swapped'")
    with pytest.raises(RuntimeError): db.query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true")


def test_validation_and_cache_never_echo_sk(flow):
    client, headers, db, calls = flow
    response = client.post('/auth/pollinations/sk/claim',headers=headers,json={'credential_record_id':'id','access_token':{'secret':'sk_do_not_echo'}})
    assert response.status_code == 422
    assert 'sk_do_not_echo' not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_existing_sk_submission_is_pending_and_cannot_adopt_duplicate(flow):
    client, headers, db, calls = flow
    response = client.post('/auth/pollinations/sk/submit', headers=headers, json={'access_token':'sk_existing_not_stored'})
    assert response.status_code == 200, response.text
    assert response.json()['verification_status'] == 'PENDING_VERIFICATION'
    assert response.json()['spending_authorized'] is False
    assert db.query('select submitted_by_owner from public.pollinations_sessions')[0]['submitted_by_owner'] == OWNER
    duplicate = client.post('/auth/pollinations/sk/submit', headers=headers, json={'access_token':'sk_existing_not_stored'})
    assert duplicate.status_code == 409
    assert len(db.query('select id from public.pollinations_sessions')) == 1
    assert client.post('/auth/pollinations/sk/submit', headers=headers, json={'access_token':'not-a-key'}).status_code == 422


def test_reference_revoked_between_provider_check_and_promotion(flow, monkeypatch):
    client, headers, db, calls = flow
    record, session, state = connected(flow)
    def identity_then_revoke(token):
        db.query("update public.soloforge_owner_accounts set verification_status='pending',verified_at=null where provider='pollinations'")
        return 200, {'sub': SUBJECT}
    monkeypatch.setattr('backend.pollinations_sk_lifecycle._userinfo', identity_then_revoke)
    result = client.post('/auth/pollinations/sk/reverify',headers=headers,json={'credential_record_id':record})
    assert result.status_code == 200, result.text
    assert result.json()['verification_status'] == 'PENDING_VERIFICATION'
    assert result.json()['provider_ownership_verified'] is False


@pytest.mark.parametrize('legacy_owner,allowed', [(GITHUB,True),(OTHER,False)])
def test_legacy_owner_mapping_requires_independent_supabase_binding(flow,legacy_owner,allowed):
    client, headers, db, calls = flow
    record = legacy(db)
    db.query('update public.pollinations_sessions set owner_user_id=$1,provider_subject=$2',[legacy_owner,SUBJECT])
    result = client.post('/auth/pollinations/sk/claim',headers=headers,json={'credential_record_id':record,'access_token':'sk_legacy'})
    assert result.status_code == (200 if allowed else 404), result.text
    assert db.query('select submitted_by_owner from public.pollinations_sessions')[0]['submitted_by_owner'] == (OWNER if allowed else None)


def test_owner_revoked_before_callback_never_exchanges_or_persists(flow, monkeypatch):
    client, headers, db, calls = flow
    login = client.get('/auth/pollinations/login', headers=headers, follow_redirects=False)
    state = parse_qs(urlsplit(login.headers['location']).query)['state'][0]
    db.query('update public.owner_v2_sessions set revoked_at=now()')
    def forbidden(*a, **k): raise AssertionError('Provider must not be called')
    monkeypatch.setattr(routes,'exchange_authorization_code', forbidden)
    response = client.get('/auth/pollinations/callback',params={'state':state,'code':'code'},follow_redirects=False)
    assert response.status_code == 401
    assert db.query('select id from public.pollinations_sessions') == []


def test_concurrent_callback_exchanges_code_once(flow, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    client, headers, db, calls = flow
    login = client.get('/auth/pollinations/login', headers=headers, follow_redirects=False)
    state = parse_qs(urlsplit(login.headers['location']).query)['state'][0]
    entered, release = threading.Event(), threading.Event()
    exchanged = []
    def provider(*args, **kwargs):
        exchanged.append(True); entered.set()
        assert release.wait(5)
        return {'access_token':'sk_concurrent','expires_in':600,'scope':'profile usage'}
    monkeypatch.setattr(routes,'exchange_authorization_code',provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(client.get,'/auth/pollinations/callback',params={'code':'code','state':state},follow_redirects=False)
        assert entered.wait(5)
        second = client.get('/auth/pollinations/callback',params={'code':'code','state':state},follow_redirects=False)
        release.set()
        assert first.result().status_code == 302
        assert second.status_code == 400
    assert len(exchanged) == 1
    assert len(db.query('select id from public.pollinations_sessions')) == 1


def test_concurrent_legacy_claim_has_one_winner(flow):
    from concurrent.futures import ThreadPoolExecutor
    client, headers, db, calls = flow
    record = legacy(db)
    db.query("update public.soloforge_owner_accounts set verification_status='pending',verified_at=null where provider='pollinations'")
    def claim():
        return client.post('/auth/pollinations/sk/claim',headers=headers,
            json={'credential_record_id':record,'access_token':'sk_legacy'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(lambda _:claim(), range(2)))
    assert statuses[0] == 200 and statuses[1] in (404,409)
    assert db.query('select submitted_by_owner from public.pollinations_sessions')[0]['submitted_by_owner'] == OWNER


def test_provider_redirects_cannot_forward_credentials(monkeypatch):
    import urllib.error
    from backend import pollinations_sk_lifecycle as lifecycle
    from backend import pollinations_oauth as oauth
    assert lifecycle._NoRedirect().redirect_request(None,None,302,'',{},'https://evil.invalid') is None
    assert oauth._NoRedirect().redirect_request(None,None,302,'',{},'https://evil.invalid') is None
    called=[]
    class RedirectingProvider:
        def open(self,request,timeout):
            called.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url,302,'redirect',{},None)
    monkeypatch.setattr(lifecycle.urllib.request,'build_opener',lambda *a:RedirectingProvider())
    status,data = lifecycle.provider_get(lifecycle.USERINFO_URL,'sk_fake')
    assert status == 302 and data == {}
    assert called == [lifecycle.USERINFO_URL]


def test_unowned_new_insert_still_denied_by_production_guard(flow):
    db=flow[2]
    with pytest.raises(RuntimeError):
        db.query("insert into public.pollinations_sessions(session_id,access_token,expires_at) values('unbound-new','sk_unbound_new',now()+interval '1 hour')")


def test_oauth_key_without_provider_expiry_enters_bounded_pending(flow, monkeypatch):
    client, headers, db, calls=flow
    monkeypatch.setattr(routes,'exchange_authorization_code',lambda *a,**k:{'access_token':'sk_without_expiry','scope':'profile usage'})
    record, session, state=connected(flow)
    row=db.query("select verification_status, expires_at > now() and expires_at <= now()+interval '601 seconds' as bounded from public.pollinations_sessions")[0]
    assert row['verification_status']=='PENDING_VERIFICATION' and row['bounded'] is True
