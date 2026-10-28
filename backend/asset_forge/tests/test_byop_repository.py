"""Actual candidate SQL + production repository/flow; network-denied, no TestClient."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
from uuid import uuid4
import wave
import pytest
from fastapi import HTTPException
from test_pollinations_owner_binding import binding_db
from backend import byop_repository as repository, byop_ledger, byop_flow, byop_runtime, byop_principal

OWNER = '11111111-1111-4111-8111-111111111111'
MEMBERS = ['22222222-2222-4222-8222-222222222222', '33333333-3333-4333-8333-333333333333']
PRINCIPALS = ['owner:' + OWNER, *['member:' + m for m in MEMBERS]]
REQUEST = {'character': 'CEO', 'generation_layout': 'single_character', 'quantity': 1,
           'pose_intent': 'presenting', 'expression': 'calm'}


def exec_fixture(db, sql):
    with db.lock:
        db.process.stdin.write(json.dumps({'sql': sql, 'exec': True}) + '\n')
        db.process.stdin.flush()
        result = json.loads(db.process.stdout.readline())
    assert 'error' not in result, result


@pytest.fixture(scope='module')
def byop_db(binding_db):
    # Existing Content Job columns used by this vertical slice; deployment must
    # separately verify the live schema. No production metadata is queried.
    schema = '''create table public.content_jobs (
      id uuid primary key default gen_random_uuid(), idea text, source text, status text,
      qa_status text, content_package jsonb, script text, audio_storage_path text,
      video_storage_path text, video_url text, render_qa jsonb, render_status text,
      render_generated_at timestamptz, retry_count integer default 0, error_message text);
    '''
    root = Path(__file__).resolve().parents[1]
    exec_fixture(binding_db, schema + (root/'sql/byop_v1_candidate.sql').read_text()
                 + (root/'sql/byop_v1_integration.sql').read_text()
                 + (root/'sql/byop_owner_pilot_candidate.sql').read_text())
    return binding_db


@pytest.fixture
def persistent(byop_db, monkeypatch):
    db = byop_db
    db.query('truncate public.byop_owner_pilot_permits,public.content_jobs,public.pollinations_sessions,public.byop_ledgers,public.soloforge_memberships,public.owner_v2_sessions,public.owner_v2_challenges,public.soloforge_owner_accounts,public.soloforge_owners')
    db.query('select public.owner_v2_bootstrap($1,$2)', [OWNER,'owner@example.test'])
    db.query("update public.soloforge_owner_accounts set provider_account_id='provider-owner', verification_status='verified',verification_evidence='independent admin fixture',verified_at=now() where provider='pollinations'")
    for index, member in enumerate(MEMBERS):
        db.query("insert into public.soloforge_memberships(user_id,status,activated_at,activation_evidence,pollinations_subject,pollinations_verified_at,pollinations_evidence) values($1,'ACTIVE',now(),'{}',$2,now(),'independent fixture')", [member,'provider-member-' + str(index)])
    for p in PRINCIPALS:
        db.query('insert into public.byop_ledgers(principal,state) values($1,$2)',
                 [p,json.dumps({'budget':100,'settled':0,'concurrency_limit':1})])

    def rest(method, path, body=None, prefer=None, **kwargs):
        if path.startswith('rpc/byop_'):
            args=','.join(f'{k} => ${i}' for i,k in enumerate(body,1))
            params=[json.dumps(v) if isinstance(v,dict) else v for v in body.values()]
            return db.query('select public.'+path.removeprefix('rpc/')+'('+args+') as value',params,'service_role')[0]['value']
        if path.startswith('byop_ledgers?'):
            from urllib.parse import parse_qs,unquote
            principal = parse_qs(path.partition('?')[2])['principal'][0].removeprefix('eq.')
            return db.query('select revision,state from public.byop_ledgers where principal=$1',[principal],'service_role')
        if path.startswith('soloforge_memberships?'):
            uid=path.split('user_id=eq.')[1].split('&')[0]
            return db.query("select user_id from public.soloforge_memberships where user_id=$1 and status='ACTIVE'",[uid],'service_role')
        raise AssertionError('Unexpected outbound transport: '+path)
    monkeypatch.setattr(repository,'supabase_request',rest)
    monkeypatch.setattr(byop_ledger,'supabase_request',rest)
    monkeypatch.setattr(byop_principal,'supabase_request',rest)

    # Supabase and Owner V2 authentication transports are fakes. The production
    # authenticate() function and server membership lookup are exercised.
    class AuthResponse:
        def __init__(self, uid): self.uid=uid
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,*args): return json.dumps({'id':self.uid,'is_anonymous':False}).encode()
    def auth_transport(request,**kwargs):
        assert request.full_url=='https://offline-auth.invalid/auth/v1/user'
        uid=request.get_header('Authorization').removeprefix('Bearer member-')
        assert uid in MEMBERS
        return AuthResponse(uid)
    monkeypatch.setenv('SUPABASE_URL','https://offline-auth.invalid')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','offline-publishable')
    monkeypatch.setattr(byop_principal.urllib.request,'urlopen',auth_transport)
    class OwnerAuthority:
        def authenticate(self, authorization):
            if authorization!='Bearer sf_owner_v2_offline': raise byop_principal.Unauthorized()
            return {'owner_id':OWNER}
    monkeypatch.setattr(byop_principal,'OwnerV2',OwnerAuthority)
    from backend import pollinations_sk_lifecycle,content_asset_generation,final_render
    monkeypatch.setattr(pollinations_sk_lifecycle,'_userinfo',lambda token:(200,{'sub':subjects[token]}))
    objects={}; subjects={}; calls=[]
    def upload_image(data,path):objects[('content-assets',path)]=data
    def upload(bucket,path,source,mime):objects[(bucket,path)]=source.read_bytes()
    def download(bucket,path,destination):destination.write_bytes(objects[(bucket,path)])
    monkeypatch.setattr(content_asset_generation,'_upload_asset',upload_image)
    monkeypatch.setattr(final_render,'_storage_upload',upload)
    monkeypatch.setattr(final_render,'_storage_download',download)
    def render_patch(method,path,body=None,**kwargs):
        assert method=='PATCH' and path.startswith('content_jobs?id=eq.')
        jid=path.split('id=eq.')[1].split('&')[0]
        columns=list(body)
        values=[json.dumps(v) if isinstance(v,dict) else v for v in body.values()]
        args=','.join(f'{c}=${i}' for i,c in enumerate(columns,1))
        return db.query('update public.content_jobs set '+args+f' where id=${len(values)+1} returning *',values+[jid],'service_role')
    monkeypatch.setattr(final_render,'_supabase_request',render_patch)
    import runtime
    forge=runtime.asset_forge_main
    master=(Path(__file__).resolve().parents[3]/'frontend/assets/characters/ceo/references/master.png').read_bytes()
    monkeypatch.setattr(forge,'_load_character_reference',lambda _:master)
    def gate():
        rows=db.query("select state from public.byop_ledgers")
        assert any(e['state']=='CALL_STARTED' for row in rows for e in row['state'].get('executions',{}).values())
    monkeypatch.setattr(forge,'require_generation_execution',gate)
    def provider(prompt,reference,token,**kwargs):
        gate();assert reference==master;assert token in subjects
        assert kwargs['settings']=={'model':'kontext','width':1024,'height':1024}
        calls.append(token)
        return master
    monkeypatch.setattr(forge,'_generate_sheet',provider)
    ledger=byop_ledger.Ledger(pricing=lambda _: {'basis':'OFFLINE FIXTURE, NOT PROVIDER PRICING',
        'maximum_micro_pollen':70,'includes_all_charges':True,'expires_at':time.time()+300})
    # Explicit offline future-member fixture: production Flow defaults to owner-only.
    # Role-policy tests restore the real policy before invoking sensitive methods.
    flow=byop_flow.Flow(byop_principal.authenticate,repository.Repository(),ledger,byop_runtime.generate,byop_runtime.render,
                        generation_policy=lambda principal: None)
    return {'db':db,'flow':flow,'subjects':subjects,'calls':calls,'objects':objects}


def auth(principal):
    return 'Bearer sf_owner_v2_offline' if principal.startswith('owner:') else 'Bearer member-'+principal.split(':')[1]


def prepared(persistent, principal):
    flow=persistent['flow']; header=auth(principal)
    token='sk_'+str(uuid4())
    persistent['subjects'][token]=flow.repository.expected_subject(principal)
    cid=flow.connect(header,token)['credential_id']
    assert flow.verify(header,cid)['verification_status']=='VERIFIED'
    job=flow.create_job(header,REQUEST,'A short CEO message.')
    consent=flow.authorize(header,cid,job['id'],80,time.time()+240)
    return header,cid,job,consent['consent_id']


@pytest.mark.parametrize('principal',PRINCIPALS)
def test_byop_persistent_vertical_slice_real_ffmpeg(persistent,principal):
    flow=persistent['flow']
    header,cid,job,consent=prepared(persistent,principal)
    eid=str(uuid4())
    asset=flow.execute(header,consent,eid)
    assert len(persistent['calls'])==1
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    image=flow.repository.asset_bytes(principal,job['id'])
    assert hashlib.sha256(image).hexdigest()==asset['sha256']
    current=flow.repository.content_job(principal,job['id'])
    assert current['content_package']['asset_forge_manifest']['generation_layout']=='single_character'
    assert current['content_package']['brand_applied'] is True
    flow.review(header,job['id'],image,False)
    with pytest.raises(ValueError):flow.render_job(header,job['id'])
    flow.review(header,job['id'],image,True)
    out=BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0\0'*16000)
    flow.repository.attach_audio(principal,job['id'],out.getvalue())
    result=flow.render_job(header,job['id'])
    assert result['render_qa']['source_asset_sha256']==asset['sha256']
    video=persistent['objects'][('content-video',result['video_storage_path'])]
    assert hashlib.sha256(video).hexdigest()==result['render_qa']['output_sha256']
    response=flow.disconnect(header,cid)
    assert response['server_revocation_confirmed'] and not response['upstream_revocation_confirmed']
    with pytest.raises(HTTPException):flow.authorize(header,cid,job['id'],80,time.time()+60)
    assert len(persistent['calls'])==1


def test_byop_repository_foreign_credentials_jobs_and_ledger_denied(persistent):
    flow=persistent['flow']; header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    for foreign in [PRINCIPALS[0],PRINCIPALS[2]]:
        assert flow.repository.credential(foreign,cid) is None
        assert flow.repository.credentials(foreign)==[]
        with pytest.raises(HTTPException):flow.job(flow.authenticate(auth(foreign)),job['id'])
        with pytest.raises(HTTPException):flow.disconnect(auth(foreign),cid)
        with pytest.raises(HTTPException):flow.execute(auth(foreign),consent,str(uuid4()))
    assert not persistent['calls']
    choices=flow.repository.credentials(PRINCIPALS[1])
    assert choices[0]['credential_id']==cid and 'access_token' not in choices[0]


@pytest.mark.parametrize('status',['PENDING','SUSPENDED','DISABLED'])
def test_byop_inactive_member_cannot_claim_reserved_execution(persistent,status):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    eid=str(uuid4());execution=flow.ledger.reserve(PRINCIPALS[1],consent,eid)
    persistent['db'].query('update public.soloforge_memberships set status=$1 where user_id=$2',[status,MEMBERS[0]])
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    with pytest.raises(HTTPException):flow.repository.claim_execution(PRINCIPALS[1],eid,execution['snapshot'],flow.ledger)
    assert not persistent['calls']


def test_byop_disconnect_before_dispatch_claim_denies_call(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    eid=str(uuid4());execution=flow.ledger.reserve(PRINCIPALS[1],consent,eid)
    flow.disconnect(header,cid)
    with pytest.raises(HTTPException):flow.repository.claim_execution(PRINCIPALS[1],eid,execution['snapshot'],flow.ledger)
    assert not persistent['calls']


def test_byop_ambiguous_outcome_retains_reservation_and_never_replays(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    def timeout(snapshot,token):persistent['calls'].append(token);raise TimeoutError()
    flow.generate=timeout;eid=str(uuid4())
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    _,state=flow.ledger.store.read(PRINCIPALS[1])
    assert state['executions'][eid]['state']=='UNKNOWN'
    assert state['executions'][eid]['reserved']==70 and len(persistent['calls'])==1


def test_byop_disconnect_failure_is_not_reported_as_success(persistent,monkeypatch):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[0])
    monkeypatch.setattr(repository,'supabase_request',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('lost response')))
    with pytest.raises(HTTPException) as exc:flow.disconnect(header,cid)
    assert exc.value.status_code==503


def test_byop_concurrent_execution_claim_has_one_provider_call(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1]);eid=str(uuid4())
    def execute(_):
        try:
            flow.execute(header,consent,eid)
            return True
        except HTTPException:
            return False
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(execute,range(2)))==1
    assert len(persistent['calls'])==1


def test_byop_started_crash_survives_repository_restart(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1]);eid=str(uuid4())
    execution=flow.ledger.reserve(PRINCIPALS[1],consent,eid)
    flow.repository.claim_execution(PRINCIPALS[1],eid,execution['snapshot'],flow.ledger)
    restarted=byop_flow.Flow(flow.authenticate,repository.Repository(),byop_ledger.Ledger(pricing=flow.ledger.pricing),
                            flow.generate,flow.render, generation_policy=flow.generation_policy)
    with pytest.raises(HTTPException):restarted.execute(header,consent,eid)
    _,state=restarted.ledger.store.read(PRINCIPALS[1])
    assert state['executions'][eid]['state']=='CALL_STARTED' and not persistent['calls']


@pytest.mark.parametrize('condition',['pending','expired','revoked'])
def test_byop_credential_state_cannot_authorize_spending(persistent,condition):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[2])
    if condition=='pending':
        persistent['db'].query("update public.pollinations_sessions set verification_status='PENDING_VERIFICATION',provider_ownership_verified=false,provider_subject=null,byop_verified_at=null where id=$1",[cid])
    elif condition=='expired':
        persistent['db'].query("update public.pollinations_sessions set expires_at=now()-interval '1 second' where id=$1",[cid])
    else:
        flow.disconnect(header,cid)
    with pytest.raises(HTTPException):flow.execute(header,consent,str(uuid4()))
    assert not persistent['calls']


def test_byop_default_pricing_remains_blocked(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[0])
    flow.ledger.pricing=byop_ledger.unavailable_pricing
    with pytest.raises(HTTPException) as e:flow.authorize(header,cid,job['id'],80,time.time()+100)
    assert e.value.status_code==503 and not persistent['calls']


def test_byop_owner_guard_and_legacy_workers_remain_separate(persistent,monkeypatch):
    from backend import soloforge_session,content_jobs_api,publishing_api,content_asset_generation
    with pytest.raises(HTTPException):soloforge_session.require_soloforge_session(auth(PRINCIPALS[1]))
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    monkeypatch.setattr(content_jobs_api,'_supabase_request',lambda *a,**k:[job])
    monkeypatch.setattr(publishing_api,'_supabase_request',lambda *a,**k:[job])
    with pytest.raises(HTTPException):content_jobs_api._get_row(job['id'])
    with pytest.raises(HTTPException):publishing_api._get_job(job['id'])
    assert content_asset_generation._process_claimed_asset(job) is False
    assert not persistent['calls']


@pytest.mark.parametrize('role',['anon','authenticated'])
def test_byop_sql_clients_cannot_call_principal_scoped_rpc(persistent,role):
    db=persistent['db'];flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    with pytest.raises(RuntimeError,match='permission denied'):
        db.query('select public.byop_credential($1,$2)',[PRINCIPALS[1],cid],role)
    with pytest.raises(RuntimeError,match='permission denied'):
        db.query("update public.soloforge_memberships set status='ACTIVE' where user_id=$1",[MEMBERS[1]],role)
    db.query('grant select on public.content_jobs to '+role)
    # With no permissive policy, RLS denies all rows. The restrictive BYOP
    # predicate also prevents a future legacy permissive policy granting access.
    assert db.query('select * from public.content_jobs',role=role)==[]


def test_byop_member_budget_never_falls_back_to_owner(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    persistent['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','5') where principal=$1",[PRINCIPALS[1]])
    with pytest.raises(HTTPException) as exc:flow.execute(header,consent,str(uuid4()))
    assert exc.value.detail=='Principal budget exhausted'
    _,owner_state=flow.ledger.store.read(PRINCIPALS[0])
    assert not owner_state.get('executions') and not persistent['calls']


def test_byop_database_expiry_blocks_dispatch_even_after_reservation(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1]);eid=str(uuid4())
    execution=flow.ledger.reserve(PRINCIPALS[1],consent,eid)
    # Administrative fixture advances the durable execution expiry without
    # waiting or altering the process clock; clients cannot perform this write.
    persistent['db'].query("update public.byop_ledgers set state=jsonb_set(state,$2,'0') where principal=$1",
                           [PRINCIPALS[1],['executions',eid,'expires_at']])
    with pytest.raises(HTTPException):flow.repository.claim_execution(PRINCIPALS[1],eid,execution['snapshot'],flow.ledger)
    assert not persistent['calls']


def test_byop_failed_reverification_demotes_prior_credential(persistent,monkeypatch):
    from backend import pollinations_sk_lifecycle
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    monkeypatch.setattr(pollinations_sk_lifecycle,'_userinfo',lambda _:(403,{}))
    assert flow.verify(header,cid)['verification_status']=='PENDING_VERIFICATION'
    with pytest.raises(HTTPException):flow.execute(header,consent,str(uuid4()))
    assert not persistent['calls']


def test_byop_job_reference_and_principal_are_sql_immutable(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    for sql,params in [
        ('update public.content_jobs set byop_principal=$1 where id=$2',[PRINCIPALS[2],job['id']]),
        ("update public.content_jobs set content_package=jsonb_set(content_package,'{asset_forge_request,quantity}','2') where id=$1",[job['id']]),
        ("update public.content_jobs set script='changed' where id=$1",[job['id']]),
    ]:
        with pytest.raises(RuntimeError,match='immutable'):persistent['db'].query(sql,params,'service_role')
    assert not persistent['calls']


def test_byop_claim_commit_with_lost_response_never_dispatches_or_replays(persistent,monkeypatch):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1]);eid=str(uuid4())
    original=repository.supabase_request
    def lost_response(method,path,body=None,**kwargs):
        result=original(method,path,body,**kwargs)
        if path=='rpc/byop_claim_execution':raise TimeoutError('commit response lost')
        return result
    monkeypatch.setattr(repository,'supabase_request',lost_response)
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    monkeypatch.setattr(repository,'supabase_request',original)
    with pytest.raises(HTTPException):flow.execute(header,consent,eid)
    _,state=flow.ledger.store.read(PRINCIPALS[1])
    assert state['executions'][eid]['state']=='CALL_STARTED' and not persistent['calls']


def test_byop_production_provider_gate_still_denies_before_network(persistent,monkeypatch):
    from backend import execution_policy
    import runtime
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1])
    monkeypatch.setattr(runtime.asset_forge_main,'require_generation_execution',execution_policy.require_generation_execution)
    with pytest.raises(HTTPException):flow.execute(header,consent,str(uuid4()))
    assert not persistent['calls']


def test_byop_sql_rejects_missing_snapshot_hash_before_call_started(persistent):
    flow=persistent['flow'];header,cid,job,consent=prepared(persistent,PRINCIPALS[1]);eid=str(uuid4())
    flow.ledger.reserve(PRINCIPALS[1],consent,eid)
    with pytest.raises(RuntimeError,match='Execution absent'):
        persistent['db'].query('select public.byop_claim_execution($1,$2,null)',[PRINCIPALS[1],eid],'service_role')
    _,state=flow.ledger.store.read(PRINCIPALS[1])
    assert state['executions'][eid]['state']=='RESERVED' and not persistent['calls']


@pytest.mark.parametrize('principal', PRINCIPALS)
def test_byop_two_own_credentials_consent_a_dispatches_a(persistent, principal, monkeypatch):
    from backend.byop_principal import require_generation_role
    flow = persistent['flow']
    header, a, job, consent = prepared(persistent, principal)
    if principal.startswith('owner:'):
        flow.generation_policy = require_generation_role
    token_a = flow.repository.credential(principal, a)['token']
    token_b = 'sk_' + str(uuid4())
    persistent['subjects'][token_b] = flow.repository.expected_subject(principal)
    b = flow.connect(header, token_b)['credential_id']
    assert flow.verify(header, b)['verification_status'] == 'VERIFIED'
    # UI can select/recover B, but /executions accepts consent/execution IDs only.
    assert flow.repository.credential(principal, b)['token'] == token_b
    monkeypatch.setenv('POLLINATIONS_API_KEY', 'sk_offline_forbidden_fallback')
    eid = str(uuid4())
    flow.execute(header, consent, eid)
    assert persistent['calls'] == [token_a]
    _, state = flow.ledger.store.read(principal)
    assert state['executions'][eid]['snapshot']['credential_id'] == a
    assert state['executions'][eid]['principal'] == principal


@pytest.mark.parametrize('principal', PRINCIPALS[1:])
def test_byop_production_role_denies_members_before_consent_or_reservation(persistent, principal):
    from backend.byop_principal import require_generation_role
    flow = persistent['flow']
    header, cid, job, old_consent = prepared(persistent, principal)
    flow.generation_policy = require_generation_role
    before = flow.ledger.store.read(principal)
    with pytest.raises(HTTPException) as exc:
        flow.authorize(header, cid, job['id'], 80, time.time() + 60)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        flow.execute(header, old_consent, str(uuid4()))
    assert exc.value.status_code == 403
    assert flow.ledger.store.read(principal) == before
    assert not persistent['calls']


def test_byop_owner_role_never_replaces_consent_or_budget(persistent):
    from backend.byop_principal import require_generation_role
    flow = persistent['flow']
    header, cid, job, consent = prepared(persistent, PRINCIPALS[0])
    flow.generation_policy = require_generation_role
    with pytest.raises(HTTPException):
        flow.execute(header, str(uuid4()), str(uuid4()))
    persistent['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','0') where principal=$1", [PRINCIPALS[0]])
    with pytest.raises(HTTPException):
        flow.execute(header, consent, str(uuid4()))
    assert not persistent['calls']


@pytest.mark.parametrize('includes_all_charges', [None, False, 'true'])
def test_byop_base_only_quote_cannot_authorize(persistent, includes_all_charges):
    flow = persistent['flow']
    header, cid, job, _ = prepared(persistent, PRINCIPALS[0])
    flow.ledger.pricing = lambda _: {'basis': 'OFFLINE ONLY', 'maximum_micro_pollen': 70,
        'expires_at': time.time() + 60, 'includes_all_charges': includes_all_charges}
    with pytest.raises(HTTPException):
        flow.authorize(header, cid, job['id'], 80, time.time() + 60)
    assert not persistent['calls']


@pytest.mark.parametrize('already_reserved', [False, True])
def test_byop_old_consent_without_all_in_quote_cannot_reserve(persistent, already_reserved):
    flow = persistent['flow']
    header, _, _, consent = prepared(persistent, PRINCIPALS[0])
    eid = str(uuid4())
    if already_reserved:
        flow.ledger.reserve(PRINCIPALS[0], consent, eid)
    revision, state = flow.ledger.store.read(PRINCIPALS[0])
    del state['consents'][consent]['quote']['includes_all_charges']
    # Simulate historical rows, not a permitted edit through the guarded RPC.
    persistent['db'].query('update public.byop_ledgers set state=$2 where principal=$1',
                           [PRINCIPALS[0], json.dumps(state)])
    with pytest.raises(HTTPException):
        flow.execute(header, consent, eid)
    assert not persistent['calls']
