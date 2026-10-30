"""Actual OAuth routes + Owner V2 + sanitized legacy SQL; no external I/O.

PGlite is SQL/WASM evidence, not native PostgreSQL or PostgREST/RLS proof.
The existing Pollinations adapter writes access_token under its retained contract;
this test does not claim application-layer encryption for that legacy column.
"""
import asyncio
from io import BytesIO
import json
from urllib.parse import parse_qs, urlsplit
import urllib.error
import httpx
import pytest
from fastapi import FastAPI
from test_pollinations_login_release import legacy_db, ddl, SQL
from backend.asset_forge.backend import pollinations_oauth_router as routes, owner_v2

OWNER = '11111111-1111-4111-8111-111111111111'
SECRET = 'sk_OFFLINE_CALLBACK_FIXTURE'


@pytest.fixture
def repair(legacy_db, monkeypatch):
    db = legacy_db
    db.query('select public.owner_v2_bootstrap($1,$2)', [OWNER,'owner@example.test'])
    monkeypatch.setenv('OWNER_V2_AUTH_ENABLED','true')
    mailbox = []
    from types import SimpleNamespace
    authority = owner_v2.OwnerV2(db.call, lambda:SimpleNamespace(send=lambda email,code:mailbox.append(code)))
    challenge = authority.request('owner@example.test')
    login = authority.verify(challenge['challenge_id'], challenge['browser_proof'], mailbox[-1])
    monkeypatch.setattr(owner_v2, 'OwnerV2', lambda:authority)
    monkeypatch.setenv('POLLINATIONS_CLIENT_ID','pk_OFFLINE_APP')
    monkeypatch.setenv('POLLINATIONS_REDIRECT_URI','https://testserver/auth/pollinations/callback')
    monkeypatch.setattr(routes, '_supabase_config', lambda:('https://offline.invalid','OFFLINE_SERVICE_KEY'))
    writes, exchanges, errors = [], [], []
    behavior = {'role':'service_role', 'exchange_error':False}
    def exchange(*args, **kwargs):
        exchanges.append(True)
        if behavior['exchange_error']: raise RuntimeError(SECRET)
        return {'access_token':SECRET, 'expires_in':600, 'scope':'profile usage'}
    monkeypatch.setattr(routes, 'exchange_authorization_code', exchange)
    def store(method, path, *, body=None, prefer=None):
        assert path.startswith('pollinations_sessions')
        if method == 'POST':
            assert path == 'pollinations_sessions?on_conflict=session_id'
            assert prefer == 'resolution=merge-duplicates,return=minimal'
            writes.append(dict(body))
            keys = list(body)
            updates = ','.join(k+'=excluded.'+k for k in keys if k != 'session_id')
            try:
                db.query('insert into public.pollinations_sessions('+','.join(keys)+') values ('+
                    ','.join('$'+str(i) for i in range(1,len(keys)+1))+') on conflict(session_id) do update set '+updates,
                    list(body.values()), behavior['role'])
            except RuntimeError as exc:
                errors.append(str(exc))
                raise
            return b''
        assert method == 'GET'
        params = parse_qs(urlsplit('/'+path).query)
        columns = params['select'][0]
        assert all(c.isalnum() or c in '_,' for c in columns)
        sid = params['session_id'][0].removeprefix('eq.')
        return json.dumps(db.query('select '+columns+' from public.pollinations_sessions where session_id=$1', [sid], 'service_role')).encode()
    monkeypatch.setattr(routes, '_supabase_request', store)
    routes._sessions.clear(); routes._transactions.clear(); routes._handoffs.clear(); routes._launches.clear()
    api = FastAPI(); api.include_router(routes.router)
    import fastapi.routing, fastapi.dependencies.utils
    async def inline(function,*args,**kwargs): return function(*args,**kwargs)
    monkeypatch.setattr(fastapi.routing,'run_in_threadpool',inline)
    monkeypatch.setattr(fastapi.dependencies.utils,'run_in_threadpool',inline)
    headers = {'Authorization':'Bearer '+login['session_token']}
    def client():
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='https://testserver',headers=headers)
    async def start(client):
        response = await client.post('/auth/pollinations/connect',json={'client':'web','return_to':'https://soloforge-ai-web.onrender.com/'})
        assert response.status_code == 200, response.text
        launch = await client.get(response.json()['launch_path'],follow_redirects=False)
        assert launch.status_code == 302
        return parse_qs(urlsplit(launch.headers['location']).query)['state'][0]
    async def callback(client,state):
        result = await client.get('/auth/pollinations/callback',params={'code':'OFFLINE_CODE','state':state},follow_redirects=False)
        assert SECRET not in result.text and SECRET not in str(result.headers)
        return result
    return SimpleNamespace(db=db,authority=authority,client=client,start=start,callback=callback,
        writes=writes,exchanges=exchanges,errors=errors,behavior=behavior,headers=headers)


def test_exact_legacy_failure_then_candidate_callback_handoff_reload(repair):
    r = repair
    async def scenario():
        async with r.client() as client:
            state = await r.start(client)
            failure = await r.callback(client,state)
            assert failure.status_code == 503 and 'Could not persist Pollinations session' in failure.text
            assert any('submitted_by_owner' in error or '42703' in error for error in r.errors)
            assert r.db.query('select count(*) as n from public.pollinations_sessions')[0]['n'] == 0
            assert not routes._sessions and not routes._handoffs
            assert (await r.callback(client,state)).status_code == 400 and len(r.exchanges) == 1
            ddl(r.db,SQL.read_text())  # ISOLATED fixture only, no production connection.
            state = await r.start(client)
            success = await r.callback(client,state)
            assert success.status_code == 302
            handoff = parse_qs(urlsplit(success.headers['location']).query)['code'][0]
            response = await client.post('/auth/pollinations/mobile/exchange',json={'code':handoff})
            assert response.status_code == 200 and SECRET not in response.text
            sid = response.json()['session_token']
            session = routes._sessions[sid]
            routes._persist_session(sid,session)  # Same record/secret is idempotent.
            assert r.db.query('select count(*) as n from public.pollinations_sessions')[0]['n'] == 1
            row = r.db.query('select submitted_by_owner,verification_status,provider_ownership_verified,spending_authorized from public.pollinations_sessions')[0]
            assert row == dict(submitted_by_owner=OWNER,verification_status='PENDING_VERIFICATION',provider_ownership_verified=False,spending_authorized=False)
            routes._sessions.clear()  # Server restart: recover using the retained DB adapter.
            status = await client.get('/auth/pollinations/status',headers={'X-Pollinations-Session':sid})
            assert status.status_code == 200 and status.json()['connected'] is True
            assert status.json()['spending_authorized'] is False and SECRET not in status.text
            assert (await client.post('/auth/pollinations/mobile/exchange',json={'code':handoff})).status_code == 400
            assert (await r.callback(client,state)).status_code == 400 and len(r.exchanges) == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('case',['mismatch','expired','wrong_owner','revoked_owner','exchange_error','permission'])
def test_failure_boundaries_preserve_one_use_and_no_secret(repair,case):
    r = repair; ddl(r.db,SQL.read_text())
    async def scenario():
        async with r.client() as client:
            state = await r.start(client)
            if case == 'mismatch':
                assert (await r.callback(client,'wrong-state')).status_code == 400
                assert not r.exchanges and not r.writes
                assert state in routes._transactions  # Another browser cannot consume it.
                return
            if case == 'expired': routes._transactions[state].created_at -= 601
            if case == 'wrong_owner': routes._transactions[state].owner_id = '22222222-2222-4222-8222-222222222222'
            if case == 'revoked_owner': r.db.query('update public.owner_v2_sessions set revoked_at=now()')
            if case == 'exchange_error': r.behavior['exchange_error'] = True
            if case == 'permission': r.behavior['role'] = 'anon'
            response = await r.callback(client,state)
            assert response.status_code == {'expired':400,'wrong_owner':403,'revoked_owner':401,'exchange_error':502,'permission':503}[case]
            assert (await r.callback(client,state)).status_code == 400
            assert r.db.query('select count(*) as n from public.pollinations_sessions')[0]['n'] == 0
            assert not routes._sessions and not routes._handoffs
            assert len(r.exchanges) == (1 if case in ('exchange_error','permission') else 0)
    asyncio.run(scenario())


def test_http_error_logs_only_status_without_secret_or_response(monkeypatch,capsys):
    monkeypatch.setattr(routes,'_supabase_config',lambda:('https://offline.invalid','OFFLINE_SERVICE_KEY'))
    def reject(*args,**kwargs):
        raise urllib.error.HTTPError('https://offline.invalid',400,SECRET,{},BytesIO(SECRET.encode()))
    monkeypatch.setattr(routes.urllib.request,'urlopen',reject)
    with pytest.raises(RuntimeError) as caught:
        routes._supabase_request('POST','pollinations_sessions',body={'access_token':SECRET})
    assert caught.value.__suppress_context__ is True
    output = capsys.readouterr().out
    assert '400' in output and 'POST' in output
    assert SECRET not in output and 'OFFLINE_SERVICE_KEY' not in output
