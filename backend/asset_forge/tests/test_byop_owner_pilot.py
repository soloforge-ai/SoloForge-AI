"""Owner pilot HTTP/SQL/builder offline slice. Never authenticates to providers.

ASGI requests execute the real routes and dependencies. Only sync task scheduling
is inline in the local HTTP fixture (AF_UNIX wakeups are forbidden here). Native
threadpool scheduling/PostgREST/storage integration still require isolated CI.
PGlite serializes SQL, so threaded claims below are NOT native row-lock proof.
"""
import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import os
import time
from types import SimpleNamespace
from uuid import uuid4
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from test_byop_repository import persistent, byop_db, binding_db, PRINCIPALS, REQUEST, auth, exec_fixture
from test_byop_pricing import evidence
from backend import byop_principal, execution_policy, byop_router, byop_repository, owner_v2
from backend.byop_pilot import bound_terms
from backend.byop_evidence import disabled_transport
import runtime

REAL_SHEET = runtime.asset_forge_main._generate_sheet


@pytest.fixture
def pilot(persistent, monkeypatch, tmp_path):
    db = persistent['db']
    if db.query("select to_regclass('public.byop_owner_pilot_permits') as t")[0]['t'] is None:
        exec_fixture(db, (Path(__file__).resolve().parents[1]/'sql/byop_owner_pilot_candidate.sql').read_text())
    db.query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','100000') where principal=$1", [PRINCIPALS[0]])
    # Real Owner V2 passwordless/session SQL; only delivery is an offline mailbox.
    monkeypatch.setenv('OWNER_V2_AUTH_ENABLED', 'true')
    mailbox = []
    authority = owner_v2.OwnerV2(db.call, lambda: SimpleNamespace(send=lambda email, code: mailbox.append(code)))
    challenge = authority.request('owner@example.test')
    login = authority.verify(challenge['challenge_id'], challenge['browser_proof'], mailbox[-1])
    monkeypatch.setattr(byop_principal, 'OwnerV2', lambda: authority)
    header = 'Bearer ' + login['session_token']
    repo = byop_repository.Repository()
    # A private filesystem storage fake, independent of application instances.
    # This proves restart-readable bytes/hash binding, not Supabase bucket RLS.
    private = tmp_path / 'private-content-assets'
    private.mkdir(mode=0o700)
    from backend import content_asset_generation, final_render
    def upload(data, path):
        target = private / path
        target.parent.mkdir(mode=0o700, exist_ok=True)
        temporary = target.with_suffix('.part')
        temporary.write_bytes(data)
        temporary.chmod(0o600)
        os.replace(temporary, target)
        persistent['objects'][('content-assets', path)] = data
    def download(bucket, path, destination):
        assert bucket == 'content-assets'
        destination.write_bytes((private/path).read_bytes())
    monkeypatch.setattr(content_asset_generation, '_upload_asset', upload)
    monkeypatch.setattr(final_render, '_storage_download', download)
    reads, calls, facts = [], [], {}
    failure = {'mode': None}
    def transport(path, token):
        # These are same-credential GET fakes; never a paid request or balance
        # substitution. The collector adds its own principal/time/key digest.
        reads.append((path, hashlib.sha256(token.encode()).hexdigest()))
        value = facts[path]
        return deepcopy(value)
    monkeypatch.setattr(runtime.asset_forge_main, '_generate_sheet', REAL_SHEET)
    monkeypatch.setattr(runtime.asset_forge_main, 'require_generation_execution', execution_policy.require_generation_execution)
    master = (Path(__file__).resolve().parents[3]/'frontend/assets/characters/ceo/references/master.png').read_bytes()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            if failure['mode'] == 'url':
                return json.dumps({'data': [{'url': 'https://offline.invalid/must-not-fetch'}]}).encode()
            return json.dumps({'data': [{'b64_json': base64.b64encode(master).decode()}]}).encode()
    def outbound(request, timeout):
        assert request.full_url == 'https://gen.pollinations.ai/v1/images/edits'
        assert request.method == 'POST' and request.get_header('Authorization') == 'Bearer ' + failure['token']
        state = db.query('select state from public.byop_ledgers where principal=$1', [PRINCIPALS[0]])[0]['state']
        assert state['executions'][failure['eid']]['state'] == 'CALL_STARTED'
        assert db.query('select consumed_at from public.byop_owner_pilot_permits')[0]['consumed_at']
        calls.append(hashlib.sha256(failure['token'].encode()).hexdigest())
        if failure['mode'] == 'timeout': raise TimeoutError()
        if failure['mode'] == 'crash': raise SystemExit('simulated process loss')
        return Response()
    def opener(handler):
        assert handler.redirect_request(None, None, None, None, None, None) is None
        return SimpleNamespace(open=outbound)
    monkeypatch.setattr(runtime.asset_forge_main.urllib.request, 'build_opener', opener)
    monkeypatch.setenv('POLLINATIONS_API_KEY', 'offline-forbidden-environment-fallback')
    flow = byop_router.get_flow(transport)
    app = FastAPI()
    app.include_router(byop_router.router)
    app.dependency_overrides[byop_router.get_evidence_transport] = lambda: transport
    yield {**persistent, 'db': db, 'flow': flow, 'app': app, 'header': header,
           'facts': facts, 'reads': reads, 'dispatches': calls, 'failure': failure,
           'authority': authority, 'repo': repo, 'private': private}
    db.query('truncate public.byop_owner_pilot_permits')


@pytest.fixture
def http(pilot, monkeypatch):
    import fastapi.routing
    import fastapi.dependencies.utils
    async def inline(function, *args, **kwargs):
        return function(*args, **kwargs)
    # Test-only scheduling adapter; no security/provider/generation gate bypass.
    monkeypatch.setattr(fastapi.routing, 'run_in_threadpool', inline)
    monkeypatch.setattr(fastapi.dependencies.utils, 'run_in_threadpool', inline)
    async def request(method, path, **kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=pilot['app']), base_url='http://offline.test') as client:
            return await client.request(method, '/v1/byop' + path, **kwargs)
    def send(method, path, **kwargs):
        kwargs.setdefault('headers', {'Authorization': pilot['header']})
        return asyncio.run(request(method, path, **kwargs))
    return send


def prepare(pilot, http):
    response = http('POST', '/credentials', json={'access_token': 'sk_offline_selected_A'})
    assert response.status_code == 200
    cid = response.json()['credential_id']
    pilot['subjects']['sk_offline_selected_A'] = 'provider-owner'
    assert http('POST', f'/credentials/{cid}/verify').status_code == 200
    job = http('POST', '/jobs', json={'asset_forge_request': REQUEST}).json()
    principal = pilot['flow'].authenticate(pilot['header'])
    snap = pilot['flow'].snapshot(principal, cid, job['id'])
    data = evidence(snap, principal.key, pilot['repo'].credential(principal.key, cid), time.time())
    pilot['facts'].update({'/models': [data['catalog']], '/account/key': data['key'], '/account/balance': data['balance']})
    consent = http('POST', f"/jobs/{job['id']}/consents", json={'credential_id': cid,
                   'maximum_micro_pollen': 40000, 'expires_at': time.time()+60})
    assert consent.status_code == 200, consent.text
    eid = str(uuid4())
    pilot['failure'].update(eid=eid, token='sk_offline_selected_A')
    return cid, job, consent.json(), {'execution_id': eid, 'consent_id': consent.json()['consent_id']}


def provision(pilot, consent, body, **changes):
    execution = {'id': body['execution_id'], 'principal': PRINCIPALS[0],
                 'snapshot': consent['snapshot'], 'consent_id': body['consent_id']}
    terms = {**bound_terms(execution, consent), 'expires_at': consent['expires_at'],
             'manual_reconciliation_accepted': True, **changes}
    # Administrative OFFLINE FIXTURE only; no issuance API/service-role insert.
    pilot['db'].query('insert into public.byop_owner_pilot_permits(execution_id,principal,terms) values($1,$2,$3)',
                      [body['execution_id'], PRINCIPALS[0], json.dumps(terms)])


def assert_held(pilot, eid, status):
    _, state = pilot['flow'].ledger.store.read(PRINCIPALS[0])
    assert state['executions'][eid]['state'] == status
    assert state['executions'][eid]['reserved'] == 30000


def test_owner_http_pilot_success_private_preview_and_a_b_binding(pilot, http):
    cid, job, consent, body = prepare(pilot, http)
    # A second owned credential does not change the consent or dispatch key.
    second = http('POST', '/credentials', json={'access_token': 'sk_offline_selected_B'}).json()['credential_id']
    pilot['subjects']['sk_offline_selected_B'] = 'provider-owner'
    assert http('POST', f'/credentials/{second}/verify').status_code == 200
    provision(pilot, consent, body)
    result = http('POST', '/executions', json=body)
    assert result.status_code == 200, result.text
    preview = http('GET', f"/jobs/{job['id']}/asset")
    assert preview.status_code == 200 and preview.headers['cache-control'] == 'no-store'
    assert hashlib.sha256(preview.content).hexdigest() == result.json()['sha256']
    assert ('content-assets', result.json()['path']) in pilot['objects']
    stored = pilot['private']/result.json()['path']
    assert stored.stat().st_mode & 0o777 == 0o600
    assert byop_repository.Repository().asset_bytes(PRINCIPALS[0], job['id']) == preview.content
    assert pilot['dispatches'] == [hashlib.sha256(b'sk_offline_selected_A').hexdigest()]
    assert len(pilot['reads']) == 6  # all three sources at consent AND dispatch
    assert all(item[1] == pilot['dispatches'][0] for item in pilot['reads'])
    assert http('POST', '/executions', json=body).status_code == 409
    assert len(pilot['dispatches']) == 1
    assert_held(pilot, body['execution_id'], 'GENERATED')
    public = http('GET', f"/jobs/{job['id']}/executions").json()['executions'][0]
    assert public['reconciliation_required'] is True
    assert http('GET', f"/jobs/{job['id']}/asset", headers={'Authorization': auth(PRINCIPALS[1])}).status_code != 200
    disconnected = http('POST', f'/credentials/{cid}/disconnect')
    assert disconnected.status_code == 200 and not disconnected.json()['upstream_revocation_confirmed']
    assert execution_policy.generation_execution_authorized() is False
    with pytest.raises(HTTPException): execution_policy.require_generation_execution()


@pytest.mark.parametrize('change', ['missing', 'credential', 'expiry', 'model', 'quote', 'consent', 'maximum'])
def test_http_invalid_permit_denies_before_dispatch(pilot, http, change):
    _, _, consent, body = prepare(pilot, http)
    changes = {'credential': {'credential_id': str(uuid4())}, 'expiry': {'expires_at': time.time()-1},
               'model': {'model': 'other/model'}, 'quote': {'quote_sha256': '0'*64},
               'consent': {'consent_id': str(uuid4())}, 'maximum': {'maximum_micro_pollen': 50000}}
    if change != 'missing': provision(pilot, consent, body, **changes[change])
    result = http('POST', '/executions', json=body)
    assert result.status_code == 503 and not pilot['dispatches']
    assert_held(pilot, body['execution_id'], 'RESERVED')


@pytest.mark.parametrize('failure', ['stale', 'funds', 'key', 'owner_revoked', 'database', 'credential_revoked'])
def test_http_dispatch_evidence_or_identity_failure_closed(pilot, http, monkeypatch, failure):
    cid, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    if failure == 'stale':
        pilot['flow'].ledger.clock = lambda: time.time()+31
        # HTTP uses fresh flows; make collector start timestamps stale in the
        # trusted adapter rather than accepting timestamps from HTTP payloads.
        from backend import byop_evidence
        original = byop_evidence.EvidenceCollector.collect
        def stale(self, *args):
            result = original(self, *args)
            result['observed_at']['key'] -= 31
            return result
        monkeypatch.setattr(byop_evidence.EvidenceCollector, 'collect', stale)
    if failure == 'funds': pilot['facts']['/account/balance']['accountBalance'] = {'tier': 0, 'paid': 0}
    if failure == 'key': pilot['facts']['/account/key']['id'] = 'changed-key'
    if failure == 'owner_revoked': pilot['authority'].logout(pilot['header'])
    if failure == 'database':
        monkeypatch.setattr(byop_repository.Repository, 'claim_owner_pilot', lambda *a: (_ for _ in ()).throw(HTTPException(503, 'Offline failed claim')))
    if failure == 'credential_revoked': pilot['repo'].disconnect(PRINCIPALS[0], cid)
    result = http('POST', '/executions', json=body)
    assert result.status_code in (401, 403, 409, 503) and not pilot['dispatches']


@pytest.mark.parametrize('mode,state', [('timeout', 'UNKNOWN'), ('url', 'UNKNOWN'), ('crash', 'CALL_STARTED')])
def test_http_ambiguous_result_or_crash_never_replays(pilot, http, mode, state):
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    pilot['failure']['mode'] = mode
    if mode == 'crash':
        with pytest.raises(SystemExit): http('POST', '/executions', json=body)
    else:
        assert http('POST', '/executions', json=body).status_code == 409
    assert_held(pilot, body['execution_id'], state)
    # New application dependency/repository instances model a restart. No
    # fixture unfreezes the consumed permit or durable CALL_STARTED state.
    assert http('POST', '/executions', json=body).status_code == 409
    replacement = {**body, 'execution_id': str(uuid4())}
    assert http('POST', '/executions', json=replacement).status_code == 409
    assert len(pilot['dispatches']) == 1


@pytest.mark.parametrize('member', PRINCIPALS[1:])
def test_http_owner_permit_never_enables_member_or_foreign_access(pilot, http, member):
    cid, job, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    headers = {'Authorization': auth(member)}
    assert http('POST', '/executions', headers=headers, json=body).status_code == 403
    assert http('POST', f"/jobs/{job['id']}/consents", headers=headers,
        json={'credential_id': cid, 'maximum_micro_pollen': 40000, 'expires_at': time.time()+10}).status_code == 403
    assert not pilot['dispatches']


def test_http_no_consent_or_default_evidence_transport_never_dispatches(pilot, http):
    _, job, _, body = prepare(pilot, http)
    assert http('POST', '/executions', json={**body, 'consent_id': str(uuid4())}).status_code == 409
    pilot['app'].dependency_overrides[byop_router.get_evidence_transport] = lambda: disabled_transport
    credentials = pilot['repo'].credentials(PRINCIPALS[0])
    assert http('POST', f"/jobs/{job['id']}/consents", json={'credential_id': credentials[0]['credential_id'],
        'maximum_micro_pollen': 40000, 'expires_at': time.time()+10}).status_code == 503
    assert not pilot['dispatches']


def test_pilot_sql_concurrent_claims_are_one_use_and_immutable(pilot, http):
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    execution = pilot['flow'].ledger.reserve(PRINCIPALS[0], body['consent_id'], body['execution_id'])
    def claim(_):
        try:
            return pilot['repo'].claim_owner_pilot(PRINCIPALS[0], execution, consent['quote'])
        except HTTPException:
            return None
    with ThreadPoolExecutor(2) as pool:
        assert sum(result is not None for result in pool.map(claim, range(2))) == 1
    assert_held(pilot, body['execution_id'], 'CALL_STARTED')
    with pytest.raises(RuntimeError):
        pilot['db'].query('update public.byop_owner_pilot_permits set consumed_at=null')
    for role in ('anon', 'authenticated', 'service_role'):
        with pytest.raises(RuntimeError, match='permission denied'):
            pilot['db'].query('insert into public.byop_owner_pilot_permits select * from public.byop_owner_pilot_permits', role=role)
    for role in ('anon', 'authenticated'):
        with pytest.raises(RuntimeError, match='permission denied'):
            pilot['db'].query('select public.byop_claim_owner_pilot($1,$2,$3,$4,$5)',
                [PRINCIPALS[0],body['execution_id'],execution['snapshot_sha256'],execution['quote_sha256'],json.dumps(consent['quote'])],role)
    assert not pilot['dispatches']


def test_http_lost_pilot_claim_response_cannot_replay(pilot, http, monkeypatch):
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    original = byop_repository.supabase_request
    def lost(method, path, data=None, **kwargs):
        result = original(method, path, data, **kwargs)
        if path == 'rpc/byop_claim_owner_pilot': raise TimeoutError('offline lost commit response')
        return result
    monkeypatch.setattr(byop_repository, 'supabase_request', lost)
    assert http('POST', '/executions', json=body).status_code == 503
    assert_held(pilot, body['execution_id'], 'CALL_STARTED')
    monkeypatch.setattr(byop_repository, 'supabase_request', original)
    assert http('POST', '/executions', json=body).status_code == 409
    assert not pilot['dispatches']


@pytest.mark.parametrize('change', ['token', 'prompt', 'reference', 'settings', 'expired'])
def test_claimed_scope_rechecks_actual_outbound_request(pilot, http, change):
    from backend.byop_pilot import owner_pilot_dispatch, claim_request
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    execution = pilot['flow'].ledger.reserve(PRINCIPALS[0], body['consent_id'], body['execution_id'])
    receipt = pilot['repo'].claim_owner_pilot(PRINCIPALS[0], execution, consent['quote'])
    credential = pilot['repo'].credential(PRINCIPALS[0], consent['snapshot']['credential_id'])
    snap = execution['snapshot']
    request = runtime.asset_forge_main.AssetForgeRequest.model_validate(snap['settings']['request'])
    prompt = runtime.asset_forge_main._build_prompt(request, 1, 1, True)
    reference = runtime.asset_forge_main._load_character_reference(request.character)
    settings = {'model': snap['model'], 'width': 1024, 'height': 1024}
    now = [time.time()]
    with owner_pilot_dispatch(receipt, execution, consent, credential, lambda: now[0]):
        if change == 'token': credential = {**credential, 'token': 'sk_offline_wrong_B'}
        if change == 'prompt': prompt += ' changed'
        if change == 'reference': reference = b'changed'
        if change == 'settings': settings['width'] = 2048
        if change == 'expired': now[0] = receipt['permit']['expires_at']+1
        with pytest.raises(HTTPException): claim_request(prompt, reference, credential['token'], settings)
    with pytest.raises(HTTPException): execution_policy.require_generation_execution()
    assert_held(pilot, body['execution_id'], 'CALL_STARTED')
    assert not pilot['dispatches']


def test_scope_allows_only_one_matching_request_and_no_context_escape(pilot, http):
    from backend.byop_pilot import owner_pilot_dispatch, claim_request
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    execution = pilot['flow'].ledger.reserve(PRINCIPALS[0], body['consent_id'], body['execution_id'])
    receipt = pilot['repo'].claim_owner_pilot(PRINCIPALS[0], execution, consent['quote'])
    credential = pilot['repo'].credential(PRINCIPALS[0], consent['snapshot']['credential_id'])
    request = runtime.asset_forge_main.AssetForgeRequest.model_validate(execution['snapshot']['settings']['request'])
    args = (runtime.asset_forge_main._build_prompt(request, 1, 1, True),
            runtime.asset_forge_main._load_character_reference(request.character), credential['token'],
            {'model': execution['snapshot']['model'], 'width': 1024, 'height': 1024})
    with owner_pilot_dispatch(receipt, execution, consent, credential, time.time):
        execution_policy.require_generation_execution()
        claim_request(*args)
        with pytest.raises(HTTPException): claim_request(*args)
        with pytest.raises(HTTPException): execution_policy.require_generation_execution()
    with pytest.raises(HTTPException): execution_policy.require_generation_execution()


def test_provider_evidence_adapter_is_read_only_bounded_and_not_default(monkeypatch):
    from backend.byop_evidence import ProviderEvidenceTransport
    reads = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, maximum):
            assert maximum == 2*1024*1024+1
            return b'{"offline": true}'
    def open_request(request, timeout):
        assert request.method == 'GET'
        assert request.full_url == 'https://gen.pollinations.ai/account/key'
        assert request.get_header('Authorization') == 'Bearer offline-selected-credential'
        assert timeout == 10
        reads.append(request.full_url)
        return Response()
    def opener(handler):
        assert handler.redirect_request(None, None, None, None, None, None) is None
        return SimpleNamespace(open=open_request)
    monkeypatch.setattr('urllib.request.build_opener', opener)
    assert ProviderEvidenceTransport()('/account/key', 'offline-selected-credential') == {'offline': True}
    with pytest.raises(HTTPException): ProviderEvidenceTransport()('/image/paid', 'offline-selected-credential')
    with pytest.raises(HTTPException): disabled_transport('/account/key', 'offline-selected-credential')
    assert len(reads) == 1 and byop_router.get_evidence_transport() is disabled_transport


def test_atomic_claim_rechecks_new_aggregate_holds_and_preserves_dispatch_evidence(pilot, http):
    _, _, consent, body = prepare(pilot, http)
    provision(pilot, consent, body)
    execution = pilot['flow'].ledger.reserve(PRINCIPALS[0], body['consent_id'], body['execution_id'])
    observed = {**consent['quote'], 'available_micro_pollen': 30000}
    # Independent administrative fixture raises concurrency only for this race.
    pilot['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{concurrency_limit}','2') where principal=$1", [PRINCIPALS[0]])
    next_consent = pilot['flow'].authorize(pilot['header'], consent['snapshot']['credential_id'],
                                         consent['snapshot']['job_id'], 40000, time.time()+20)
    pilot['flow'].ledger.reserve(PRINCIPALS[0], next_consent['consent_id'], str(uuid4()))
    with pytest.raises(HTTPException):
        pilot['repo'].claim_owner_pilot(PRINCIPALS[0], execution, observed)
    assert_held(pilot, body['execution_id'], 'RESERVED')
    assert pilot['db'].query('select consumed_at from public.byop_owner_pilot_permits')[0]['consumed_at'] is None
    receipt = pilot['repo'].claim_owner_pilot(PRINCIPALS[0], execution, consent['quote'])
    assert receipt['execution']['dispatch_evidence'] == consent['quote']
    revision, state = pilot['flow'].ledger.store.read(PRINCIPALS[0])
    state['executions'][body['execution_id']]['dispatch_evidence']['available_micro_pollen'] = 9999999
    with pytest.raises(RuntimeError, match='immutable'):
        pilot['flow'].ledger.store.cas(PRINCIPALS[0], revision, state)
    assert not pilot['dispatches']
