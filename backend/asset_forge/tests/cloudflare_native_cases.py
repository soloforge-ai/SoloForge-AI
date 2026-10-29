"""Native PostgreSQL + actual app-runtime AES-GCM. Manual isolated CI only."""
from concurrent.futures import ThreadPoolExecutor
import json
import secrets
import time
from uuid import uuid4
from threading import Barrier, Event
import pytest
from fastapi import HTTPException
import test_cloudflare_persistence as contracts
from test_cloudflare_persistence import (
    context, verified, execution, OWNER, MEMBER, ACCOUNT, TOKEN,
    test_ciphertext_pending_scoping_and_restart,
    test_atomic_revocation_before_claim_denies_transport,
    test_revalidation_restart_and_no_replay,
    test_permissions_identity_and_verification_guards,
    test_verified_reload_dispatch_exact_token_and_revoke_after_claim,
    test_member_persistence_and_suspension_never_owner_fallback,
    test_identity_and_lost_claim_response_hold_reservation,
    test_pollinations_remains_isolated_after_schema_extension,
)
from backend.byop_secret import SecretBox
from backend.byop_runtime import cloudflare_mock_dispatch
from cloudflare_native_fixture import disposable_database, connection


class AppCrypto(SecretBox):
    def __init__(self, key=None):
        self.key=key or secrets.token_bytes(32)
        super().__init__({'fixture-v1':self.key},'fixture-v1')


@pytest.fixture(autouse=True)
def actual_crypto(monkeypatch):
    import sys, cryptography
    assert sys.version_info[:2]==(3,12)
    assert cryptography.__version__=='46.0.3'
    monkeypatch.setattr(contracts,'ExistingSystemCrypto',AppCrypto)


@pytest.fixture
def database():
    with disposable_database(contracts.sanitized_schema()) as holder:
        db=holder['db']
        db.query('select public.owner_v2_bootstrap($1,$2)',[OWNER.split(':')[1],'offline-owner@example.test'])
        db.query("insert into public.soloforge_memberships(user_id,status,activated_at,activation_evidence) values($1,'ACTIVE',now(),'{}')",[MEMBER.split(':')[1]])
        db.query('insert into public.byop_ledgers(principal,state) values($1,$2)',[OWNER,json.dumps(
            {'provider':'cloudflare','unit':'neurons','budget':100,'settled':0,'concurrency_limit':1})])
        yield holder


def test_native_independent_connections_claim_once(context):
    holder,repo,_,_,_=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    gate=Barrier(2); calls=[]
    def run():
        gate.wait(timeout=5)
        try:
            return cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,
                fake_transport=lambda **kw: (calls.append(kw['token']),contracts.image())[1])
        except HTTPException: return None
    # query() creates independent connections; no fixture lock serializes them.
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(run) for _ in range(2)]
        results=[f.result(timeout=20) for f in futures]
    assert sum(r is not None for r in results)==1 and calls==[TOKEN]
    state=ledger.store.read(OWNER)[1]['executions'][exe['id']]
    assert state['state']=='GENERATED' and state['reserved']==70


def test_native_revocation_lock_wins_before_claim(context):
    holder,repo,rest,_,_=context
    rid=verified(context); ledger,exe,cred=execution(context,rid)
    ready,proceed=Event(),Event()
    def intercepted(method,path,body=None,**kwargs):
        if path=='rpc/byop_cloudflare_claim':
            ready.set()
            if not proceed.wait(timeout=10): raise RuntimeError('Claim barrier timed out')
        return rest(method,path,body,**kwargs)
    ledger.store.offline_transport=intercepted
    def attempt():
        with pytest.raises(HTTPException):
            cloudflare_mock_dispatch(ledger,OWNER,exe,cred,'cat',repository=repo,
                fake_transport=lambda **_: pytest.fail('revoked dispatch'))
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(attempt)
        assert ready.wait(timeout=10)  # authoritative reload already completed
        with connection(holder['db'].name) as conn:
            conn.execute('select id from public.pollinations_sessions where id=%s for update',(rid,))
            conn.execute('update public.pollinations_sessions set byop_revoked_at=clock_timestamp() where id=%s',(rid,))
            proceed.set()
            deadline=time.monotonic()+5
            while True:
                conn.execute('select pg_stat_clear_snapshot()')
                waiting=conn.execute("select count(*) from pg_stat_activity where datname=%s and pid<>pg_backend_pid() and wait_event_type='Lock' and position('byop_cloudflare_claim' in query)>0",(holder['db'].name,)).fetchone()[0]
                if waiting: break
                if time.monotonic()>deadline: pytest.fail('Independent claim did not wait on credential lock')
                time.sleep(.05)
        future.result(timeout=20)
    state=ledger.store.read(OWNER)[1]['executions'][exe['id']]
    assert state['state']=='RESERVED' and state['reserved']==70


def test_native_aggregate_reservations_use_independent_connections(context):
    holder,_,_,_,_=context
    rid=verified(context)
    ledger,consent,credential=execution(context,rid,reserve=False)
    second=ledger.consent(OWNER,consent['snapshot'],80,time.time()+300,credential=credential)
    gate=Barrier(2)
    def reserve(consent_id):
        gate.wait(timeout=5)
        try: return ledger.reserve(OWNER,consent_id,str(uuid4()))
        except HTTPException: return None
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(reserve,c['consent_id']) for c in (consent,second)]
        results=[f.result(timeout=20) for f in futures]
    assert sum(r is not None for r in results)==1
    state=ledger.store.read(OWNER)[1]
    assert sum(e['reserved'] for e in state['executions'].values())==70


def test_actual_application_aesgcm_aad_and_wrong_key():
    box=AppCrypto(); rid='offline-credential'
    key_id,ciphertext=box.encrypt(TOKEN,OWNER,ACCOUNT,rid)
    assert box.decrypt(key_id,ciphertext,OWNER,ACCOUNT,rid)==TOKEN
    for principal,account,record in ((MEMBER,ACCOUNT,rid),(OWNER,'b'*32,rid),(OWNER,ACCOUNT,'other')):
        with pytest.raises(ValueError): box.decrypt(key_id,ciphertext,principal,account,record)
    with pytest.raises(ValueError): AppCrypto().decrypt(key_id,ciphertext,OWNER,ACCOUNT,rid)


def test_native_rls_denies_rows_even_with_fixture_table_grants(context):
    holder,repo,_,_,_=context
    rid=repo.submit_cloudflare(OWNER,ACCOUNT,TOKEN)['credential_id']
    db=holder['db']
    assert db.query("select relrowsecurity from pg_class where oid='public.pollinations_sessions'::regclass")[0]['relrowsecurity'] is True
    # Grants below exist ONLY inside this disposable test database, to distinguish
    # native RLS denial from mere absence of table privileges.
    db.query('grant select,update on public.pollinations_sessions to anon,authenticated')
    try:
        for role in ('anon','authenticated'):
            assert db.query('select id from public.pollinations_sessions',role=role)==[]
            assert db.query('update public.pollinations_sessions set spending_authorized=true returning id',role=role)==[]
    finally:
        db.query('revoke select,update on public.pollinations_sessions from anon,authenticated')
    assert db.query('select spending_authorized from public.pollinations_sessions where id=$1',[rid])[0]['spending_authorized'] is False
