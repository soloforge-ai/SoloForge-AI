"""Offline provider contract tests. No secrets or network transport."""
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from io import BytesIO
from threading import Lock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from PIL import Image
from backend.byop_ledger import Ledger
from backend.byop_runtime import cloudflare_mock_dispatch
from backend.cloudflare_image import MODEL

OWNER = 'owner:offline-owner'

class Store:
    def __init__(self):
        self.lock = Lock()
        self.revision = 0
        self.state = {'provider': 'cloudflare', 'unit': 'neurons', 'budget': 100, 'concurrency_limit': 1}
    def read(self, principal):
        assert principal == OWNER
        with self.lock:
            return self.revision, deepcopy(self.state)
    def cas(self, principal, revision, state):
        assert principal == OWNER
        with self.lock:
            if revision != self.revision:
                return False
            self.revision += 1
            self.state = deepcopy(state)
            return True

@pytest.fixture
def case():
    store = Store()
    quote = {'provider': 'cloudflare', 'unit': 'neurons', 'maximum_neurons': 70,
             'includes_all_charges': True, 'basis': 'OFFLINE ONLY', 'expires_at': 1200}
    ledger = Ledger(store, lambda _: deepcopy(quote), lambda: 1000, provider='cloudflare', unit='neurons')
    credential = {'id': 'A', 'provider': 'cloudflare', 'principal': OWNER, 'account_id': 'offline-account',
                  'token': 'OFFLINE-NOT-A-SECRET', 'verification_status': 'VERIFIED',
                  'provider_ownership_verified': True, 'expires_at': 1200}
    snapshot = {'credential_id': 'A', 'job_id': 'offline-job', 'revision': 1, 'operation': 'text_image',
                'provider': 'cloudflare', 'budget_unit': 'neurons', 'account_id': 'offline-account',
                'credential_sha256': hashlib.sha256(credential['token'].encode()).hexdigest(),
                'model': MODEL, 'image_count': 1, 'prompt_sha256': hashlib.sha256(b'cat').hexdigest(),
                'reference_sha256': hashlib.sha256(b'').hexdigest(), 'settings': {'steps': 4}}
    return ledger, credential, snapshot, quote

def reserve(case):
    ledger, credential, snapshot, _ = case
    consent = ledger.consent(OWNER, snapshot, 80, 1100, credential=credential)
    return ledger.reserve(OWNER, consent['consent_id'], str(uuid4()))

def image(**kwargs):
    output = BytesIO(); Image.new('RGB', (8, 8)).save(output, 'PNG')
    return {'status': 200, 'result': {'image': base64.b64encode(output.getvalue()).decode()}}

def test_success_held_reservation_and_immutable_selection(case):
    ledger, credential, snap, _ = case
    execution = reserve(case)
    snap['model'] = 'UI changed'
    calls = []
    def transport(**kwargs):
        assert ledger.store.read(OWNER)[1]['executions'][execution['id']]['state'] == 'CALL_STARTED'
        calls.append(kwargs); return image()
    data, meta = cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=transport)
    assert hashlib.sha256(data).hexdigest() == meta['sha256']
    assert meta['ceo_identity_verified'] is False
    assert calls[0]['model'] == MODEL
    state = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert state['state'] == 'GENERATED' and state['reserved'] == 70
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=transport)
    assert len(calls) == 1

@pytest.mark.parametrize('change', [None, {'principal': 'member:foreign'}, {'provider': 'pollinations'},
    {'token': ''}, {'id': 'B'}, {'account_id': 'other'}, {'verification_status': 'PENDING_VERIFICATION'},
    {'revoked': True}, {'expires_at': 999}])
def test_invalid_credentials_never_dispatch(case, change):
    ledger, credential, _, _ = case
    execution = reserve(case)
    credential = None if change is None else {**credential, **change}
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **_: pytest.fail('dispatch'))
    assert ledger.store.read(OWNER)[1]['executions'][execution['id']]['state'] == 'RESERVED'

@pytest.mark.parametrize('response', [{'status': 429}, {'status': 500}, {'status': 200, 'result': {'image': 'bad'}}, {'status': 200}])
def test_error_quota_malformed_unknown_no_replay(case, response):
    ledger, credential, _, _ = case
    execution = reserve(case); calls = []
    def transport(**_): calls.append(1); return response
    for _ in range(2):
        with pytest.raises(HTTPException):
            cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=transport)
    state = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert state['state'] == 'UNKNOWN' and state['reserved'] == 70 and len(calls) == 1

@pytest.mark.parametrize('crash', [TimeoutError, KeyboardInterrupt])
def test_timeout_and_process_crash_never_replay(case, crash):
    ledger, credential, _, _ = case
    execution = reserve(case)
    def transport(**_): raise crash()
    with pytest.raises((HTTPException, KeyboardInterrupt)):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=transport)
    state = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert state['state'] in ('UNKNOWN', 'CALL_STARTED') and state['reserved'] == 70
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=image)

def test_budget_unit_and_default_denial(case):
    ledger, credential, snapshot, quote = case
    ledger.store.state['budget'] = 1
    with pytest.raises(HTTPException): reserve(case)
    ledger.store.state['budget'] = 100
    execution = reserve(case)
    with pytest.raises(HTTPException): cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat')
    with pytest.raises(HTTPException): Ledger(provider='cloudflare', unit='neurons')
    quote['unit'] = 'micro_pollen'
    with pytest.raises(HTTPException): ledger.consent(OWNER, snapshot, 80, 1100, credential=credential)
    ledger.store.state['unit'] = 'micro_pollen'
    with pytest.raises(HTTPException): ledger.start(OWNER, execution['id'], execution['snapshot'])

def test_concurrent_dispatch_one_winner(case):
    ledger, credential, _, _ = case
    execution = reserve(case); calls = []
    def run():
        try:
            return cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **kw: (calls.append(1), image())[1])
        except HTTPException: return None
    with ThreadPoolExecutor(2) as pool: list(pool.map(lambda _: run(), range(2)))
    assert len(calls) == 1

@pytest.mark.parametrize('mutation', [{'provider': 'pollinations'}, {'budget_unit': 'micro_pollen'}, {'credential_id': 'B'}, {'operation': 'ceo_image'}])
def test_consent_rejects_provider_unit_credential_and_ceo_mismatch(case, mutation):
    ledger, credential, snapshot, _ = case
    snapshot.update(mutation)
    with pytest.raises(HTTPException):
        ledger.consent(OWNER, snapshot, 80, 1100, credential=credential)
    assert not ledger.store.state.get('consents')

def test_no_consent_no_reservation_no_dispatch(case):
    ledger, credential, snapshot, _ = case
    with pytest.raises(HTTPException): ledger.reserve(OWNER, str(uuid4()), str(uuid4()))
    execution = {'id': str(uuid4()), 'snapshot': snapshot}
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **_: pytest.fail('dispatch'))

def test_pollinations_budget_cannot_be_reused(case):
    ledger, credential, snapshot, _ = case
    ledger.store.state.pop('provider'); ledger.store.state.pop('unit')
    with pytest.raises(HTTPException): ledger.consent(OWNER, snapshot, 80, 1100, credential=credential)

@pytest.mark.parametrize('replacement', [{'id': 'B', 'token': 'OFFLINE-TOKEN-B'}, {'token': 'OFFLINE-TOKEN-B'}])
def test_exact_token_a_and_b_mismatch(case, replacement):
    ledger, credential, _, _ = case
    execution = reserve(case)
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, {**credential, **replacement}, 'cat',
                                 fake_transport=lambda **_: pytest.fail('B must never dispatch'))
    seen = []
    cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat',
        fake_transport=lambda **kw: (seen.append(kw['token']), image())[1])
    assert seen == ['OFFLINE-NOT-A-SECRET']
    assert hashlib.sha256(seen[0].encode()).hexdigest() == execution['snapshot']['credential_sha256']

@pytest.mark.parametrize('mode', ['reject', 'raise_before', 'lost_after'])
def test_claim_failure_never_transports(case, monkeypatch, mode):
    ledger, credential, _, _ = case
    execution = reserve(case)
    original = ledger.store.cas
    def cas(principal, revision, state):
        if state['executions'][execution['id']]['state'] == 'CALL_STARTED':
            if mode == 'reject': return False
            if mode == 'lost_after': assert original(principal, revision, state)
            raise RuntimeError('offline claim acknowledgment unavailable')
        return original(principal, revision, state)
    monkeypatch.setattr(ledger.store, 'cas', cas)
    with pytest.raises((HTTPException, RuntimeError)):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **_: pytest.fail('claim unconfirmed'))
    current = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert current['reserved'] == 70
    assert current['state'] == ('CALL_STARTED' if mode == 'lost_after' else 'RESERVED')
    if mode == 'lost_after':
        with pytest.raises(HTTPException):
            cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **_: pytest.fail('replay'))

@pytest.mark.parametrize('lost_after', [False, True])
@pytest.mark.parametrize('provider_success', [False, True])
def test_outcome_persistence_failure_never_returns_success_or_replays(case, monkeypatch, lost_after, provider_success):
    ledger, credential, _, _ = case
    execution = reserve(case); calls = []
    original = ledger.store.cas
    def cas(principal, revision, state):
        if state['executions'][execution['id']]['state'] in ('GENERATED', 'UNKNOWN'):
            if lost_after: assert original(principal, revision, state)
            raise RuntimeError('offline outcome acknowledgment unavailable')
        return original(principal, revision, state)
    monkeypatch.setattr(ledger.store, 'cas', cas)
    def transport(**_):
        calls.append(1)
        return image() if provider_success else {'status': 500}
    for _ in range(2):
        with pytest.raises((HTTPException, RuntimeError)):
            cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=transport)
    current = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert current['reserved'] == 70 and len(calls) == 1
    assert current['state'] == (('GENERATED' if provider_success else 'UNKNOWN') if lost_after else 'CALL_STARTED')

@pytest.mark.parametrize('mutation', [{'token': 'OFFLINE-TOKEN-B'}, {'revoked': True}])
def test_credential_changes_during_claim_never_dispatch(case, monkeypatch, mutation):
    ledger, credential, _, _ = case
    execution = reserve(case)
    original = ledger.store.cas
    def cas(principal, revision, state):
        result = original(principal, revision, state)
        if result and state['executions'][execution['id']]['state'] == 'CALL_STARTED':
            credential.update(mutation)
        return result
    monkeypatch.setattr(ledger.store, 'cas', cas)
    with pytest.raises(HTTPException):
        cloudflare_mock_dispatch(ledger, OWNER, execution, credential, 'cat', fake_transport=lambda **_: pytest.fail('changed credential dispatched'))
    current = ledger.store.read(OWNER)[1]['executions'][execution['id']]
    assert current['state'] in ('CALL_STARTED', 'UNKNOWN') and current['reserved'] == 70
