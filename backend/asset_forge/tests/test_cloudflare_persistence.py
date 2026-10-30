"""Real SQL/WASM + AES-GCM, injected transport only. Not native PG/PostgREST proof."""
import ast
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from test_owner_v2 import Database
from test_byop_repository import exec_fixture
from test_cloudflare_image import image
from backend.byop_repository import Repository
from backend.byop_ledger import Ledger, SupabaseLedger
from backend.byop_runtime import cloudflare_mock_dispatch
from backend.cloudflare_image import MODEL

ROOT = Path(__file__).resolve().parents[3]
OWNER = 'owner:11111111-1111-4111-8111-111111111111'
MEMBER = 'member:22222222-2222-4222-8222-222222222222'
ACCOUNT = 'a' * 32
TOKEN = 'OFFLINE-CLOUDFLARE-TOKEN-A'

class ExistingSystemCrypto:
    """Test fixture only: system Python has cryptography; app venv does not.

    Exercise actual SecretBox/AESGCM via private pipes, no secret args/env/files.
    Do not add a subprocess-based production crypto implementation.
    """
    def __init__(self, key=None):
        self.key = key or secrets.token_bytes(32)
    def call(self, operation, *args):
        code = '''import importlib.util,json,sys,base64
spec=importlib.util.spec_from_file_location("box",sys.argv[1]); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
x=json.load(sys.stdin)
try:
 box=mod.SecretBox({'fixture-v1':base64.b64decode(x['key'])},'fixture-v1')
 print(json.dumps({'result':getattr(box,x['operation'])(*x['args'])}))
except Exception:
 print(json.dumps({'error':'Decryption unavailable'}))
'''
        result = subprocess.run(['/usr/bin/python3','-c',code,str(ROOT/'backend/asset_forge/backend/byop_secret.py')],
            input=json.dumps({'key':base64.b64encode(self.key).decode(),'operation':operation,'args':args}),
            text=True,capture_output=True,timeout=10,check=True)
        output=json.loads(result.stdout)
        if 'error' in output: raise ValueError('Secret unavailable')
        return output['result']
    def encrypt(self,*args): return self.call('encrypt',*args)
    def decrypt(self,*args): return self.call('decrypt',*args)

def sanitized_schema():
    source = ast.parse(Path(__file__).with_name('test_pollinations_owner_binding.py').read_text())
    legacy = next(n.value for n in ast.walk(source) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'create schema auth;' in n.value)
    sqlroot=ROOT/'backend/asset_forge/sql'
    schema=(ROOT/'supabase/migrations/20261024151629_owner_identity_v2.sql').read_text()+legacy
    schema+=(sqlroot/'pollinations_owner_binding.sql').read_text()
    schema+='create table public.content_jobs(id uuid primary key,script text,content_package jsonb);'
    schema+=(sqlroot/'byop_v1_candidate.sql').read_text()+(sqlroot/'byop_v1_integration.sql').read_text()
    schema+=(sqlroot/'byop_cloudflare_persistence_candidate.sql').read_text()
    return schema


@pytest.fixture
def database(tmp_path):
    schema = sanitized_schema()
    snapshot=tmp_path/'schema.sql'; snapshot.write_text(schema)
    dbpath=tmp_path/'db'; process=None
    def boot(reopen=False):
        nonlocal process
        if process:
            process.stdin.close(); assert process.wait(timeout=15)==0
        process=subprocess.Popen(['node',str(Path(__file__).with_name('owner_v2_pg_bridge.mjs')),str(snapshot),str(dbpath),'reopen' if reopen else 'initial'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        assert json.loads(process.stdout.readline())=={'ready':True}
        return Database(process)
    db=boot()
    db.query('select public.owner_v2_bootstrap($1,$2)',[OWNER.split(':')[1],'offline-owner@example.test'])
    db.query("insert into public.soloforge_memberships(user_id,status,activated_at,activation_evidence) values($1,'ACTIVE',now(),'{}')",[MEMBER.split(':')[1]])
    db.query('insert into public.byop_ledgers(principal,state) values($1,$2)',[OWNER,json.dumps({'provider':'cloudflare','unit':'neurons','budget':100,'settled':0,'concurrency_limit':1})])
    holder={'db':db,'boot':boot}
    try: yield holder
    finally:
        process.stdin.close(); assert process.wait(timeout=15)==0

@pytest.fixture
def context(database):
    def rpc(name,**params):
        args=','.join(f'{k} => ${i}' for i,k in enumerate(params,1))
        values=[json.dumps(v) if isinstance(v,dict) else v for v in params.values()]
        return database['db'].query('select public.byop_'+name+'('+args+') as value',values,'service_role')[0]['value']
    def rest(method,path,body=None,**kwargs):
        if path.startswith('rpc/byop_'): return rpc(path.removeprefix('rpc/byop_'),**body)
        from urllib.parse import unquote
        principal=unquote(path.split('principal=eq.')[1].split('&')[0])
        return database['db'].query('select revision,state from public.byop_ledgers where principal=$1',[principal],'service_role')
    cipher=ExistingSystemCrypto()
    repo=Repository(secret_box=cipher,offline_rpc=rpc)
    return database,repo,rest,rpc,cipher

def verified(context):
    holder,repo,rest,rpc,cipher=context
    rid=repo.submit_cloudflare(OWNER,ACCOUNT,TOKEN)['credential_id']
    holder['db'].query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true,provider_subject=provider_account_id,byop_verified_at=now(),independent_verification_evidence='independent administrative OFFLINE fixture' where id=$1",[rid])
    return rid

def execution(context,rid, *, reserve=True):
    _,repo,rest,_,_=context
    credential=repo.cloudflare_credential(OWNER,rid)
    snapshot={'provider':'cloudflare','budget_unit':'neurons','credential_id':rid,'account_id':ACCOUNT,
      'credential_sha256':hashlib.sha256(TOKEN.encode()).hexdigest(),'job_id':str(uuid4()),'revision':1,
      'operation':'text_image','model':MODEL,'image_count':1,'prompt_sha256':hashlib.sha256(b'cat').hexdigest(),
      'reference_sha256':hashlib.sha256(b'').hexdigest(),'settings':{'steps':4}}
    clock=time.time
    ledger=Ledger(SupabaseLedger(offline_transport=rest),lambda _: {'provider':'cloudflare','unit':'neurons',
        'maximum_neurons':70,'includes_all_charges':True,'basis':'OFFLINE ONLY','expires_at':clock()+300},clock,
        provider='cloudflare',unit='neurons')
    consent=ledger.consent(OWNER,snapshot,80,clock()+300,credential=credential)
    return ledger,(ledger.reserve(OWNER,consent['consent_id'],str(uuid4())) if reserve else consent),credential

def test_ciphertext_pending_scoping_and_restart(context):
    holder,repo,rest,rpc,cipher=context
    rid=repo.submit_cloudflare(OWNER,ACCOUNT,TOKEN)['credential_id']
    row=holder['db'].query('select * from public.pollinations_sessions where id=$1',[rid])[0]
    assert TOKEN not in json.dumps(row) and row['access_token'].startswith('encrypted:v1:')
    assert not row['spending_authorized'] and row['verification_status']=='PENDING_VERIFICATION'
    assert repo.cloudflare_credential(MEMBER,rid) is None
    assert rpc('credential',p_principal=OWNER,p_id=rid) is None
    assert not rpc('credentials',p_principal=OWNER)
    with pytest.raises(HTTPException): execution(context,rid)
    holder['db']=holder['boot'](True)
    restarted=Repository(secret_box=ExistingSystemCrypto(cipher.key),offline_rpc=rpc)
    assert restarted.cloudflare_credential(OWNER,rid)['token']==TOKEN
    with pytest.raises(ValueError):
        cipher.decrypt(row['secret_key_id'],row['secret_ciphertext'],MEMBER,ACCOUNT,rid)
    with pytest.raises(ValueError):
        ExistingSystemCrypto().decrypt(row['secret_key_id'],row['secret_ciphertext'],OWNER,ACCOUNT,rid)

def test_atomic_revocation_before_claim_denies_transport(context):
    holder,repo,rest,rpc,_=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    def raced(method,path,body=None,**kw):
        if path=='rpc/byop_cloudflare_claim': repo.disconnect_cloudflare(OWNER,rid)
        return rest(method,path,body,**kw)
    ledger.store.offline_transport=raced
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,fake_transport=lambda **_: pytest.fail('revoked dispatch'))
    state=ledger.store.read(OWNER)[1]['executions'][exe['id']]
    assert state['state']=='RESERVED' and state['reserved']==70
    assert repo.cloudflare_credential(OWNER,rid)['revoked']

def test_revalidation_restart_and_no_replay(context):
    holder,repo,rest,rpc,cipher=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    seen=[]
    def timeout(**kw): seen.append(kw['token']); raise TimeoutError()
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,fake_transport=timeout)
    holder['db']=holder['boot'](True)
    restarted=Repository(secret_box=ExistingSystemCrypto(cipher.key),offline_rpc=rpc)
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=restarted,fake_transport=lambda **_: pytest.fail('replay'))
    current=ledger.store.read(OWNER)[1]['executions'][exe['id']]
    assert seen==[TOKEN] and current['state']=='UNKNOWN' and current['reserved']==70

def test_permissions_identity_and_verification_guards(context):
    holder,repo,_,rpc,_=context; db=holder['db']
    rid=repo.submit_cloudflare(OWNER,ACCOUNT,TOKEN)['credential_id']
    for role in ('anon','authenticated'):
        with pytest.raises(RuntimeError): db.query('select * from public.pollinations_sessions',role=role)
        with pytest.raises(RuntimeError): db.query('select public.byop_cloudflare_credential($1,$2)',[OWNER,rid],role)
    with pytest.raises(RuntimeError):
        db.query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true,provider_subject=provider_account_id,byop_verified_at=now(),independent_verification_evidence='client forged' where id=$1",[rid],'service_role')
    with pytest.raises(RuntimeError): db.query("update public.pollinations_sessions set provider_account_id=$1 where id=$2",['b'*32,rid])
    with pytest.raises(HTTPException): repo.submit_cloudflare(MEMBER,ACCOUNT,TOKEN)
    with pytest.raises(HTTPException): Repository().submit_cloudflare(OWNER,ACCOUNT,TOKEN)
    with pytest.raises(HTTPException): repo.disconnect_cloudflare(MEMBER,rid)
    assert repo.disconnect_cloudflare(OWNER,rid)['upstream_revocation_confirmed'] is False
    with pytest.raises(RuntimeError): db.query('update public.pollinations_sessions set byop_revoked_at=null where id=$1',[rid])

def test_verified_reload_dispatch_exact_token_and_revoke_after_claim(context):
    holder,repo,rest,rpc,cipher=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    holder['db']=holder['boot'](True)
    repo=Repository(secret_box=ExistingSystemCrypto(cipher.key),offline_rpc=rpc)
    # Stale supplied data is not authoritative; selected snapshot ID is reloaded.
    stale={**cred,'token':'OFFLINE-WRONG-TOKEN'}
    seen=[]
    def transport(**kw):
        state=ledger.store.read(OWNER)[1]['executions'][exe['id']]
        assert state['state']=='CALL_STARTED'
        repo.disconnect_cloudflare(OWNER,rid)
        seen.append(kw['token']); return image()
    data,meta=cloudflare_mock_dispatch(ledger,OWNER,exe,stale,'cat',repository=repo,fake_transport=transport)
    assert seen==[TOKEN] and hashlib.sha256(data).hexdigest()==meta['sha256']
    assert ledger.store.read(OWNER)[1]['executions'][exe['id']]['reserved']==70
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,stale,'cat',repository=repo,fake_transport=lambda **_: pytest.fail('replay'))


def test_member_persistence_and_suspension_never_owner_fallback(context):
    holder,repo,_,_,_=context
    rid=repo.submit_cloudflare(MEMBER,ACCOUNT,'OFFLINE-MEMBER-TOKEN')['credential_id']
    assert repo.cloudflare_credential(MEMBER,rid)['principal']==MEMBER
    assert repo.cloudflare_credential(OWNER,rid) is None
    holder['db'].query("update public.soloforge_memberships set status='SUSPENDED' where user_id=$1",[MEMBER.split(':')[1]])
    with pytest.raises(HTTPException): repo.cloudflare_credential(MEMBER,rid)


def test_identity_and_lost_claim_response_hold_reservation(context):
    holder,repo,rest,rpc,_=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    def lost(method,path,body=None,**kw):
        result=rest(method,path,body,**kw)
        if path=='rpc/byop_cloudflare_claim': raise RuntimeError('offline lost acknowledgment')
        return result
    ledger.store.offline_transport=lost
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,fake_transport=lambda **_: pytest.fail('unconfirmed claim'))
    assert ledger.store.read(OWNER)[1]['executions'][exe['id']]['state']=='CALL_STARTED'
    ledger.store.offline_transport=rest
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,fake_transport=lambda **_: pytest.fail('replay'))
    assert ledger.store.read(OWNER)[1]['executions'][exe['id']]['reserved']==70


def test_pollinations_remains_isolated_after_schema_extension(context):
    holder,repo,_,rpc,_=context
    result=rpc('submit',p_principal=OWNER,p_token='sk_OFFLINE_POLLINATIONS',p_session='offline-pollinations-session')
    rid=result['credential_id']
    row=rpc('credential',p_principal=OWNER,p_id=rid)
    assert row['credential_provider']=='pollinations' and row['secret_ciphertext'] is None
    assert row['access_token']=='sk_OFFLINE_POLLINATIONS' and not row['spending_authorized']
    assert repo.cloudflare_credential(OWNER,rid) is None
    assert rpc('disconnect',p_principal=OWNER,p_id=rid) is True
