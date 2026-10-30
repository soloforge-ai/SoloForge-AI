"""Owner V2 -> BYOP -> existing Content Job/storage/review, offline ASGI only.

Inline sync scheduling is test-only for the sandbox socketpair limitation.
SQL uses PGlite; no new native/production verification is claimed here.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from fastapi import FastAPI
from test_byop_repository import persistent, byop_db, binding_db, exec_fixture, OWNER, MEMBERS
from test_cloudflare_persistence import ExistingSystemCrypto, ACCOUNT
from test_cloudflare_image import image
from backend import byop_router, byop_repository, byop_principal, owner_v2
from backend.byop_ledger import Ledger, SupabaseLedger
from backend.cloudflare_flow import CloudflareFlow
from backend.cloudflare_image import MODEL

TOKEN='OFFLINE-APPLICATION-CF-TOKEN'
PRINCIPAL='owner:'+OWNER

@pytest.fixture(scope='module')
def application_db(byop_db):
    root=Path(__file__).resolve().parents[1]/'sql'
    exec_fixture(byop_db,(root/'byop_cloudflare_persistence_candidate.sql').read_text()
                 +(root/'byop_cloudflare_application_candidate.sql').read_text())
    return byop_db

@pytest.fixture
def app(application_db,persistent,monkeypatch):
    db=application_db
    db.query('update public.byop_ledgers set state=$1 where principal=$2',[json.dumps(
        {'provider':'cloudflare','unit':'neurons','budget':100,'settled':0,'concurrency_limit':1}),PRINCIPAL])
    def rpc(name,**params):
        args=','.join(f'{k} => ${i}' for i,k in enumerate(params,1))
        values=[json.dumps(v) if isinstance(v,dict) else v for v in params.values()]
        return db.query('select public.byop_'+name+'('+args+') as value',values,'service_role')[0]['value']
    def rest(method,path,body=None,**kwargs):
        if path.startswith('rpc/byop_'): return rpc(path.removeprefix('rpc/byop_'),**body)
        from urllib.parse import unquote
        p=unquote(path.split('principal=eq.')[1].split('&')[0])
        return db.query('select revision,state from public.byop_ledgers where principal=$1',[p],'service_role')
    monkeypatch.setattr(byop_repository,'supabase_request',rest)
    monkeypatch.setenv('OWNER_V2_AUTH_ENABLED','true')
    mailbox=[]
    authority=owner_v2.OwnerV2(db.call,lambda: SimpleNamespace(send=lambda email,code:mailbox.append(code)))
    challenge=authority.request('owner@example.test')
    login=authority.verify(challenge['challenge_id'],challenge['browser_proof'],mailbox[-1])
    monkeypatch.setattr(byop_principal,'OwnerV2',lambda:authority)
    header={'Authorization':'Bearer '+login['session_token']}
    calls=[]; failure={'mode':None}
    def transport(**kwargs):
        calls.append(kwargs)
        if failure['mode']=='timeout': raise TimeoutError(TOKEN)
        return image()
    repo=byop_repository.Repository(secret_box=ExistingSystemCrypto(),offline_rpc=rpc)
    ledger=Ledger(SupabaseLedger(offline_transport=rest),lambda _: {'provider':'cloudflare','unit':'neurons',
        'maximum_neurons':70,'includes_all_charges':True,'basis':'OFFLINE TRUSTED FIXTURE ONLY','expires_at':time.time()+300},
        provider='cloudflare',unit='neurons')
    flow=CloudflareFlow(repo,ledger,transport)
    api=FastAPI(); api.include_router(byop_router.router)
    api.dependency_overrides[byop_router.get_cloudflare_capability]=lambda:flow
    import fastapi.routing,fastapi.dependencies.utils
    async def inline(function,*args,**kwargs): return function(*args,**kwargs)
    monkeypatch.setattr(fastapi.routing,'run_in_threadpool',inline)
    monkeypatch.setattr(fastapi.dependencies.utils,'run_in_threadpool',inline)
    async def request(method,path,**kwargs):
        kwargs.setdefault('headers',header)
        params=kwargs.pop('params',{}); params['provider']='cloudflare'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='http://offline.test') as client:
            response=await client.request(method,'/v1/byop'+path,params=params,**kwargs)
            assert TOKEN not in response.text if response.headers.get('content-type','').startswith('application/json') else True
            return response
    def http(method,path,**kwargs): return asyncio.run(request(method,path,**kwargs))
    return {'db':db,'api':api,'http':http,'flow':flow,'repo':repo,'ledger':ledger,'calls':calls,'failure':failure,'login':login}

def prepare(app,verified=True):
    h=app['http']
    submit=h('POST','/credentials',json={'access_token':TOKEN,'account_id':ACCOUNT})
    assert submit.status_code==200,submit.text
    cid=submit.json()['credential_id']
    assert submit.json()['verification_status']=='PENDING_VERIFICATION'
    # Administrative offline evidence only; no verification API or live check.
    if verified:
        app['db'].query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true,provider_subject=provider_account_id,byop_verified_at=now(),independent_verification_evidence='OFFLINE independent fixture' where id=$1",[cid])
    response=h('POST','/jobs',json={'asset_forge_request':{'prompt':'A cat on a quiet street','model':MODEL}})
    assert response.status_code==200,response.text
    return cid,response.json()['id']

def authorize(app,cid,jid,**changes):
    return app['http']('POST',f'/jobs/{jid}/consents',json={'credential_id':cid,
        'maximum_neurons':80,'expires_at':time.time()+200,**changes})

def test_owner_http_vertical_slice_to_existing_review_and_revoke(app):
    h=app['http']; assert app['login']['identity_version']=='owner_v2'
    session=h('GET','/session'); assert session.status_code==200 and session.json()['cloudflare_offline_available']
    cid,jid=prepare(app)
    assert h('GET','/credentials').json()['credentials'][0]['credential_id']==cid
    consent=authorize(app,cid,jid); assert consent.status_code==200,consent.text
    body={'consent_id':consent.json()['consent_id'],'execution_id':str(uuid4())}
    result=h('POST','/executions',json=body); assert result.status_code==200,result.text
    job=h('GET',f'/jobs/{jid}').json(); assert job['status']=='READY_FOR_REVIEW'
    assert job['content_package']['ceo_identity_required'] is False
    preview=h('GET',f'/jobs/{jid}/asset'); assert preview.status_code==200
    sha=hashlib.sha256(preview.content).hexdigest(); assert sha==result.json()['sha256']
    review=h('POST',f'/jobs/{jid}/asset-review',json={'decision':'APPROVED','asset_sha256':sha})
    assert review.status_code==200,review.text
    assert h('GET',f'/jobs/{jid}').json()['status']=='ASSET_READY'
    assert h('POST','/executions',json=body).status_code==409 and len(app['calls'])==1
    assert app['calls'][0]['token']==TOKEN and app['calls'][0]['model']==MODEL
    assert h('POST',f'/credentials/{cid}/disconnect',json={}).json()['upstream_revocation_confirmed'] is False
    assert h('GET',f'/credentials/{cid}').json()['connected'] is False
    assert app['ledger'].store.read(PRINCIPAL)[1]['executions'][body['execution_id']]['reserved']==70

@pytest.mark.parametrize('header',[{}, {'Authorization':'Bearer forged'}, {'Authorization':'Bearer member-'+MEMBERS[0]}])
def test_non_owner_cannot_submit_or_execute(app,header):
    h=app['http']
    assert h('POST','/credentials',headers=header,json={'access_token':TOKEN,'account_id':ACCOUNT}).status_code in (401,403)
    assert h('POST','/executions',headers=header,json={'consent_id':str(uuid4()),'execution_id':str(uuid4())}).status_code in (401,403)
    assert not app['calls']

def test_pending_revoked_budget_model_and_unit_denial(app):
    h=app['http']; cid,jid=prepare(app,verified=False)
    assert authorize(app,cid,jid).status_code==403
    assert h('POST','/jobs',json={'asset_forge_request':{'prompt':'cat','model':'invalid'}}).status_code==400
    assert h('POST',f'/credentials/{cid}/verify').status_code==403
    app['db'].query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true,provider_subject=provider_account_id,byop_verified_at=now(),independent_verification_evidence='OFFLINE fixture' where id=$1",[cid])
    assert authorize(app,cid,jid,maximum_micro_pollen=80).status_code==400
    consent=authorize(app,cid,jid).json()
    app['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','1') where principal=$1",[PRINCIPAL])
    assert h('POST','/executions',json={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}).status_code==409
    h('POST',f'/credentials/{cid}/disconnect')
    assert authorize(app,cid,jid).status_code==403 and not app['calls']

def test_timeout_is_sanitized_no_replay_and_reservation_held(app):
    cid,jid=prepare(app); consent=authorize(app,cid,jid).json()
    body={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}
    app['failure']['mode']='timeout'
    for _ in range(2): assert app['http']('POST','/executions',json=body).status_code==409
    assert len(app['calls'])==1
    state=app['ledger'].store.read(PRINCIPAL)[1]['executions'][body['execution_id']]
    assert state['state']=='UNKNOWN' and state['reserved']==70

def test_default_app_has_no_cloudflare_capability(app):
    app['api'].dependency_overrides.clear()
    assert app['http']('GET','/session').status_code==503
    assert not app['calls']

def test_cross_principal_missing_consent_immutable_job_and_review_reject(app):
    h=app['http']; cid,jid=prepare(app)
    foreign=app['repo'].submit_cloudflare('member:'+MEMBERS[0],ACCOUNT,'OFFLINE-FOREIGN-TOKEN')['credential_id']
    assert h('GET',f'/credentials/{foreign}').status_code==404
    assert authorize(app,foreign,jid).status_code==403
    assert h('POST','/executions',json={'consent_id':str(uuid4()),'execution_id':str(uuid4())}).status_code==409
    consent=authorize(app,cid,jid).json()
    with pytest.raises(RuntimeError):
        app['db'].query("update public.content_jobs set byop_model='other-model' where id=$1",[jid],'service_role')
    body={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}
    assert h('POST','/executions',json=body).status_code==200
    preview=h('GET',f'/jobs/{jid}/asset'); sha=hashlib.sha256(preview.content).hexdigest()
    assert h('POST',f'/jobs/{jid}/asset-review',json={'decision':'APPROVED','asset_sha256':'0'*64}).status_code==409
    assert h('POST',f'/jobs/{jid}/asset-review',json={'decision':'REJECTED','asset_sha256':sha}).status_code==200
    assert h('GET',f'/jobs/{jid}').json()['content_package']['asset_review_status']=='REJECTED'
    assert h('POST',f'/jobs/{jid}/audio',content=b'not audio').status_code==503
    assert h('POST',f'/jobs/{jid}/render',json={}).status_code==503


def test_failed_asset_persistence_is_unknown_without_replay(app,monkeypatch):
    from backend import content_asset_generation
    def fail(*args): raise RuntimeError(TOKEN)
    monkeypatch.setattr(content_asset_generation,'_upload_asset',fail)
    cid,jid=prepare(app); consent=authorize(app,cid,jid).json()
    body={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}
    for _ in range(2): assert app['http']('POST','/executions',json=body).status_code==409
    current=app['ledger'].store.read(PRINCIPAL)[1]['executions'][body['execution_id']]
    assert current['state']=='UNKNOWN' and current['reserved']==70 and len(app['calls'])==1


def test_concurrent_http_execution_has_one_dispatch(app):
    cid,jid=prepare(app); consent=authorize(app,cid,jid).json()
    body={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda _: app['http']('POST','/executions',json=body),range(2)))
    assert sum(r.status_code==200 for r in responses)==1 and len(app['calls'])==1
    loser=next(r for r in responses if r.status_code!=200)
    # Native independent connections can both see RESERVED before one claims it.
    # A rejected/lost claim acknowledgement deliberately returns fail-closed 503.
    assert loser.status_code in (409,503)
    if loser.status_code==503:
        assert loser.json()['detail']=='Cloudflare claim unconfirmed; no dispatch'
    assert app['http']('POST','/executions',json=body).status_code==409
    state=app['ledger'].store.read(PRINCIPAL)[1]['executions'][body['execution_id']]
    assert state['state']=='GENERATED' and state['reserved']==70 and len(app['calls'])==1
