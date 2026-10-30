"""Explicit CI only: native PG17 migration + actual isolated PostgREST HTTP."""
import asyncio
from io import BytesIO
import hashlib
import json
from urllib.parse import parse_qs,urlsplit
import urllib.error
from uuid import uuid4
import pytest
import test_pollinations_login_release as migration
import test_pollinations_callback_persistence_repair as callback
from test_pollinations_login_release import (
    test_preserves_legacy_and_denies_spending_and_client_access,
    test_duplicate_preflight_rolls_back_without_row_loss,
    test_release_template_is_pinned_manual_and_execution_disabled,
)
from test_pollinations_callback_persistence_repair import (
    repair, OWNER, SECRET, routes,
    test_exact_legacy_failure_then_candidate_callback_handoff_reload,
    test_failure_boundaries_preserve_one_use_and_no_secret,
    test_http_error_logs_only_status_without_secret_or_response,
)
from pollinations_native_fixture import (
    legacy_schema,execute_ddl,jwt,rest_service,reload_schema,disposable_database,
)


@pytest.fixture
def legacy_db():
    with disposable_database(legacy_schema()) as holder:
        yield holder['db']


@pytest.fixture(autouse=True)
def native_ddl(monkeypatch):
    monkeypatch.setattr(migration,'ddl',execute_ddl)
    monkeypatch.setattr(callback,'ddl',execute_ddl)


def test_native_partial_migration_rejected_atomically(legacy_db):
    db=legacy_db
    migration.seed(db)
    db.query('alter table public.pollinations_sessions add column submitted_by_owner uuid')
    with pytest.raises(RuntimeError,match='Already or partially migrated'):
        execute_ddl(db,migration.SQL.read_text())
    assert db.query('select count(*) as n from public.pollinations_sessions')[0]['n']==1
    assert not db.query("select column_name from information_schema.columns where table_name='pollinations_sessions' and column_name='credential_digest'")


def test_native_digest_and_immutable_identity(legacy_db):
    db=legacy_db
    db.query('select public.owner_v2_bootstrap($1,$2)',[OWNER,'owner@example.test'])
    execute_ddl(db,migration.SQL.read_text())
    rid=db.query("insert into public.pollinations_sessions(session_id,access_token,submitted_by_owner,expires_at) values('native-session',$1,$2,now()+interval '1 hour') returning id,credential_digest",[SECRET,OWNER])[0]
    assert rid['credential_digest']==hashlib.sha256(SECRET.encode()).hexdigest()
    for statement,params in (
        ('update public.pollinations_sessions set access_token=$1 where id=$2',[SECRET+'-B',rid['id']]),
        ('update public.pollinations_sessions set submitted_by_owner=null where id=$1',[rid['id']]),
        ('update public.pollinations_sessions set spending_authorized=true where id=$1',[rid['id']]),
    ):
        with pytest.raises(RuntimeError): db.query(statement,params,'service_role')
    assert db.query('select spending_authorized from public.pollinations_sessions')[0]['spending_authorized'] is False


def test_native_cloudflare_additions_preserve_pollinations_history(legacy_db):
    import ast
    from pathlib import Path
    db=legacy_db;migration.seed(db)
    before=db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions')
    assert hashlib.sha256(migration.SQL.read_bytes()).hexdigest()=='9583e4f8db8359a8eb0a50d295d01f66ce4d9ce0a063eee609c46d7f0c415f7b'
    execute_ddl(db,migration.SQL.read_text())
    tree=ast.parse(Path(__file__).with_name('test_byop_repository.py').read_text())
    jobs=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'create table public.content_jobs (' in n.value)
    execute_ddl(db,jobs)
    root=migration.SQL.parent
    for name in ('byop_v1_candidate.sql','byop_v1_integration.sql','byop_owner_pilot_candidate.sql',
                 'byop_cloudflare_persistence_candidate.sql','byop_cloudflare_application_candidate.sql'):
        execute_ddl(db,(root/name).read_text())
    assert db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions')==before
    row=db.query('select credential_provider,spending_authorized from public.pollinations_sessions')[0]
    assert row=={'credential_provider':'pollinations','spending_authorized':False}
    assert db.query("select to_regprocedure('public.byop_cloudflare_claim(text,uuid,jsonb,text)') is not null as present")[0]['present'] is True


def test_postgrest_schema_cache_and_real_upsert(repair,monkeypatch,capsys):
    r=repair
    # Start PostgREST BEFORE migration, exactly reproducing the missing contract.
    with rest_service(r.db) as rest:
        diagnostics=[]
        headers={'Authorization':'Bearer '+jwt()}
        missing=rest.post('/pollinations_sessions',headers=headers,json={
            'session_id':'legacy-contract','access_token':SECRET,'submitted_by_owner':OWNER})
        assert missing.status_code==400 and missing.json()['code']=='PGRST204'
        execute_ddl(r.db,migration.SQL.read_text())
        reload_schema(r.db,rest)
        # Exercise the ACTUAL Supabase byte adapter over real PostgREST UDS HTTP.
        # Only the local URL routing is injected; request body/headers are retained.
        # repair() replaces that function, so recover the unbound implementation
        # captured at module import below, never a new production adapter.
        production_request=REAL_SUPABASE_REQUEST
        monkeypatch.setattr(routes,'_supabase_config',lambda:('https://offline.invalid',jwt()))
        class Response(BytesIO):
            def __enter__(self): return self
            def __exit__(self,*args): self.close()
        def local_http(request,**kwargs):
            assert request.full_url.startswith('https://offline.invalid/rest/v1/')
            path=request.full_url.removeprefix('https://offline.invalid/rest/v1')
            response=rest.request(request.get_method(),path,headers=dict(request.header_items()),content=request.data)
            if response.status_code>=400:
                code=response.json().get('code','unknown')
                diagnostics.append((response.status_code,code if isinstance(code,str) and code.isalnum() else 'unclassified'))
                raise urllib.error.HTTPError('http://isolated.test',response.status_code,'storage rejected',{},BytesIO(response.content))
            return Response(response.content)
        monkeypatch.setattr(routes.urllib.request,'urlopen',local_http)
        monkeypatch.setattr(routes,'_supabase_request',production_request)
        async def scenario():
            async with r.client() as client:
                state=await r.start(client)
                response=await r.callback(client,state)
                assert response.status_code==302, diagnostics
                handoff=parse_qs(urlsplit(response.headers['location']).query)['code'][0]
                exchanged=await client.post('/auth/pollinations/mobile/exchange',json={'code':handoff})
                assert exchanged.status_code==200 and SECRET not in exchanged.text
                sid=exchanged.json()['session_token']
                routes._persist_session(sid,routes._sessions[sid])
                routes._sessions.clear()
                status=await client.get('/auth/pollinations/status',headers={'X-Pollinations-Session':sid})
                assert status.status_code==200 and status.json()['connected'] is True
                assert status.json()['spending_authorized'] is False
                r.db.query("insert into public.pollinations_sessions(session_id,access_token,owner_user_id,provider_subject,expires_at) values('unbound-legacy','sk_OFFLINE_LEGACY','33333333-3333-4333-8333-333333333333','legacy-subject',now()+interval '1 hour')")
                assert (await client.get('/auth/pollinations/status',headers={'X-Pollinations-Session':'unbound-legacy'})).status_code==404
                assert (await r.callback(client,state)).status_code==400 and len(r.exchanges)==1
                r.db.query('update public.owner_v2_sessions set revoked_at=now()')
                assert (await client.get('/auth/pollinations/status',headers={'X-Pollinations-Session':sid})).status_code==401
                assert (await client.get('/auth/pollinations/status',headers={'Authorization':'Bearer wrong-owner','X-Pollinations-Session':sid})).status_code==401
        asyncio.run(scenario())
        assert r.db.query('select count(*) as n from public.pollinations_sessions')[0]['n']==2
        assert SECRET not in capsys.readouterr().out


# Capture before repair fixtures monkeypatch it; this is the existing adapter.
REAL_SUPABASE_REQUEST=routes._supabase_request


def test_postgrest_client_roles_rls_and_non_superuser_authenticator(repair):
    r=repair;execute_ddl(r.db,migration.SQL.read_text())
    r.db.query("insert into public.pollinations_sessions(session_id,access_token,submitted_by_owner,expires_at) values('rls-session',$1,$2,now()+interval '1 hour')",[SECRET,OWNER])
    with rest_service(r.db) as rest:
        for auth in (None,jwt('authenticated',subject='22222222-2222-4222-8222-222222222222')):
            headers={} if auth is None else {'Authorization':'Bearer '+auth}
            assert rest.get('/pollinations_sessions',headers=headers).status_code in (401,403)
            assert rest.post('/rpc/pollinations_reverify',headers=headers,json={
                'p_owner_id':OWNER,'p_record_id':str(uuid4()),'p_subject':'foreign','p_identity_verified':True}).status_code in (401,403)
        assert rest.get('/pollinations_sessions',headers={'Authorization':'Bearer '+jwt('postgres')}).status_code in (401,403)
        assert rest.get('/pollinations_sessions',headers={'Authorization':'Bearer invalid-signature'}).status_code==401
        # Fixture-only grants distinguish actual RLS denial from missing grants.
        r.db.query('grant select,update on public.pollinations_sessions to anon,authenticated')
        try:
            for auth in (None,jwt('authenticated')):
                headers={} if auth is None else {'Authorization':'Bearer '+auth}
                response=rest.get('/pollinations_sessions',headers=headers)
                assert response.status_code==200 and response.json()==[]
                updated=rest.patch('/pollinations_sessions',headers={**headers,'Prefer':'return=representation'},json={'spending_authorized':True})
                assert updated.status_code==200 and updated.json()==[]
        finally:
            r.db.query('revoke select,update on public.pollinations_sessions from anon,authenticated')
    assert r.db.query('select spending_authorized from public.pollinations_sessions')[0]['spending_authorized'] is False


def test_postgrest_reverify_rpc_and_legacy_preservation(repair):
    r=repair;migration.seed(r.db)
    before=r.db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions')
    execute_ddl(r.db,migration.SQL.read_text())
    assert r.db.query('select id,session_id,access_token,owner_user_id,provider_subject,expires_at from public.pollinations_sessions')==before
    rid=r.db.query("insert into public.pollinations_sessions(session_id,access_token,submitted_by_owner,expires_at) values('rpc-session',$1,$2,now()+interval '1 hour') returning id",[SECRET,OWNER])[0]['id']
    r.db.query("update public.soloforge_owner_accounts set provider_account_id='independent-subject',verification_status='verified',verified_at=now(),verification_evidence='OFFLINE independent fixture' where provider='pollinations'")
    with rest_service(r.db) as rest:
        headers={'Authorization':'Bearer '+jwt()}
        body={'p_owner_id':OWNER,'p_record_id':rid,'p_subject':'foreign','p_identity_verified':True}
        response=rest.post('/rpc/pollinations_reverify',headers=headers,json=body)
        assert response.status_code==200 and response.json()['verification_status']=='PENDING_VERIFICATION'
        body['p_subject']='independent-subject'
        response=rest.post('/rpc/pollinations_reverify',headers=headers,json=body)
        assert response.status_code==200 and response.json()['verification_status']=='VERIFIED'
        assert response.json()['spending_authorized'] is False
        body['p_owner_id']='22222222-2222-4222-8222-222222222222'
        response=rest.post('/rpc/pollinations_reverify',headers=headers,json=body)
        assert response.status_code==200 and response.json() is None
        r.db.query("update public.soloforge_owners set status='disabled'")
        body['p_owner_id']=OWNER
        response=rest.post('/rpc/pollinations_reverify',headers=headers,json=body)
        assert response.status_code==200 and response.json() is None
    assert r.db.query('select spending_authorized from public.pollinations_sessions where id=$1',[rid])[0]['spending_authorized'] is False
