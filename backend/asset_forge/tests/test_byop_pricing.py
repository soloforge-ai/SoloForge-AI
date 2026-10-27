"""Offline provider evidence, existing SQL/ledger and Owner Flow integration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from backend.byop_pricing import EvidencePricing, CANONICAL_MODEL, same_reviewed_model
from backend.byop_principal import require_generation_role
from backend.byop_ledger import digest
from backend.byop_ledger import Ledger
from test_byop_repository import persistent, byop_db, binding_db, PRINCIPALS, prepared


def evidence(snapshot, principal, credential, now):
    return {
        'principal': principal, 'credential_id': snapshot['credential_id'],
        'credential_digest': hashlib.sha256(credential['token'].encode()).hexdigest(),
        'observed_at': dict.fromkeys(('catalog', 'key', 'balance'), now),
        'catalog': {'name': CANONICAL_MODEL, 'aliases': ['kontext'], 'community': False,
                    'publisher': 'Black Forest Labs', 'supported_endpoints': ['/v1/images/edits'],
                    'health': {'status': 'healthy', 'success_rate': 100, 'requests': 20},
                    'paid_only': False, 'pricing': {'currency': 'pollen', 'completionImageTokens': '0.03'}},
        'key': {'id': 'provider-key-A', 'userId': credential['provider_subject'],
                'valid': True, 'type': 'secret', 'permissions': {'models': ['image']},
                'pollenBudget': 1, 'questPollenOnly': False, 'byopApp': None,
                'expiresAt': datetime.fromtimestamp(now + 600, timezone.utc).isoformat()},
        'balance': {'balance': 1, 'accountBalance': {'tier': 1, 'paid': 0, 'total': 1}},
    }


@pytest.fixture
def facts():
    snapshot = {'credential_id': 'A', 'job_id': 'job', 'revision': 1, 'operation': 'ceo_image',
                'model': 'kontext', 'image_count': 1, 'prompt_sha256': 'a'*64,
                'reference_sha256': 'b'*64, 'settings': {'image_width': 1024, 'image_height': 1024}}
    credential = {'token': 'sk_offline_A', 'principal': PRINCIPALS[0],
                  'provider_subject': 'payer', 'verification_status': 'VERIFIED',
                  'provider_ownership_verified': True}
    data = evidence(snapshot, PRINCIPALS[0], credential, 1000)
    return snapshot, credential, data, EvidencePricing(lambda _: deepcopy(data), lambda: 1000)


@pytest.mark.parametrize('app,expected', [
    (None, 30000), ({'clientKeyId': 'app', 'appUser': 'payer'}, 30000),
    ({'clientKeyId': 'app', 'appUser': 'other-developer'}, 37500),
])
def test_verified_flat_rate_and_conservative_markup(facts, app, expected):
    snapshot, credential, data, pricing = facts
    data['key']['byopApp'] = app
    quote = pricing(snapshot)
    pricing.validate_context(PRINCIPALS[0], snapshot, quote, credential)
    assert quote['maximum_micro_pollen'] == expected
    assert quote['includes_all_charges'] and not quote['earnings_confirmed']
    assert quote['expires_at'] == 1030


@pytest.mark.parametrize('path,value', [
    (('observed_at','catalog'), 969), (('observed_at','key'), 969), (('observed_at','balance'), 969),
    (('observed_at','catalog'), 1001), (('observed_at','catalog'), float('nan')), (('observed_at',), None),
    (('catalog','pricing','completionImageTokens'), '0.04'),
    (('catalog','pricing','promptImageTokens'), '0.001'),
    (('catalog','pricing','currency'), 'usd'), (('catalog','pricing_variants'), [{'price': 'unknown'}]),
    (('catalog','pricing_units'), {'completionImageTokens': {'unit': 'megapixel'}}),
    (('key','valid'), False), (('key','pollenBudget'), None), (('key','pollenBudget'), float('inf')),
    (('key','expiresAt'), '1970-01-01T00:00:00+00:00'),
    (('key','permissions'), {}), (('key','permissions','models'), ['text']),
    (('key','byopApp'), {}), (('balance','accountBalance'), None),
    (('credential_id',), 'B'), (('principal',), PRINCIPALS[1]),
])
def test_missing_changed_stale_or_incomplete_contract_fails_closed(facts, path, value):
    snapshot, _, data, pricing = facts
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(HTTPException) as exc:
        pricing(snapshot)
    assert exc.value.status_code == 503


@pytest.mark.parametrize('path,value', [
    (('key','pollenBudget'), '0.02999999'), (('balance','balance'), '0.02999999'),
    (('balance','accountBalance'), {'tier': '0.02', 'paid': '0.02'}),
])
def test_budget_rounds_down_and_account_buckets_are_never_pooled(facts, path, value):
    snapshot, _, data, pricing = facts
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(HTTPException) as exc:
        pricing(snapshot)
    assert exc.value.status_code == 409


@pytest.mark.parametrize('field,value', [('model','flux'), ('image_count',2), ('operation','text')])
def test_unreviewed_request_never_infers_price_from_model_name(facts, field, value):
    snapshot, _, _, pricing = facts
    snapshot[field] = value
    with pytest.raises(HTTPException):
        pricing(snapshot)


def test_different_dimensions_are_not_assumed_to_have_a_supported_contract(facts):
    snapshot, _, _, pricing = facts
    snapshot['settings']['image_width'] = 2048
    with pytest.raises(HTTPException):
        pricing(snapshot)


def test_quote_cannot_bind_foreign_principal_or_credential_b(facts):
    snapshot, credential, _, pricing = facts
    quote = pricing(snapshot)
    for principal, record in [(PRINCIPALS[1], credential),
                              (PRINCIPALS[0], {**credential, 'token': 'sk_offline_B'})]:
        with pytest.raises(HTTPException):
            pricing.validate_context(principal, snapshot, quote, record)


def test_dispatch_rechecks_budget_identity_freshness_and_aggregate_holds(facts):
    snapshot, credential, data, pricing = facts
    quote = pricing(snapshot)
    pricing.validate_dispatch(PRINCIPALS[0], snapshot, quote, credential, 30000)
    data['key']['pollenBudget'] = '0.04'
    with pytest.raises(HTTPException):
        pricing.validate_dispatch(PRINCIPALS[0], snapshot, quote, credential, 60000)
    data['key']['id'] = 'provider-key-B'
    with pytest.raises(HTTPException):
        pricing.validate_dispatch(PRINCIPALS[0], snapshot, quote, credential, 30000)
    data['observed_at']['key'] = 900
    with pytest.raises(HTTPException):
        pricing.validate_dispatch(PRINCIPALS[0], snapshot, quote, credential, 30000)


def configure(persistent):
    flow = persistent['flow']
    header, cid, job, _ = prepared(persistent, PRINCIPALS[0])
    flow.generation_policy = require_generation_role
    snapshot = flow.snapshot(flow.authenticate(header), cid, job['id'])
    record = flow.repository.credential(PRINCIPALS[0], cid)
    data = evidence(snapshot, PRINCIPALS[0], record, time.time())
    flow.ledger.pricing = EvidencePricing(lambda _: deepcopy(data), time.time)
    persistent['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','100000') where principal=$1", [PRINCIPALS[0]])
    consent = flow.authorize(header, cid, job['id'], 40000, time.time() + 60)
    return flow, header, cid, job, data, consent


def test_owner_evidence_quote_uses_existing_reservation_and_call_started(persistent):
    flow, header, cid, job, data, consent = configure(persistent)
    a = flow.repository.credential(PRINCIPALS[0], cid)['token']
    b = flow.connect(header, 'sk_offline_B')['credential_id']
    assert b != cid  # UI selection cannot rewrite A's consent.
    reads = []
    reader = flow.ledger.pricing.reader
    def read(snapshot):
        reads.append(snapshot['credential_id'])
        return reader(snapshot)
    flow.ledger.pricing.reader = read
    eid = str(uuid4())
    flow.execute(header, consent['consent_id'], eid)
    assert persistent['calls'] == [a]
    assert reads == [cid]
    _, state = flow.ledger.store.read(PRINCIPALS[0])
    execution = state['executions'][eid]
    assert execution['reserved'] == 30000 and execution['state'] == 'GENERATED'
    assert execution['quote_sha256'] == digest(consent['quote'])
    with pytest.raises(HTTPException):
        flow.execute(header, consent['consent_id'], eid)
    assert persistent['calls'] == [a]
    assert reads == [cid]  # No new provider evidence/generation after a started call.


@pytest.mark.parametrize('change', ['stale', 'budget', 'key', 'principal'])
def test_changed_dispatch_evidence_never_reaches_call_started(persistent, change):
    flow, header, _, _, data, consent = configure(persistent)
    if change == 'stale': data['observed_at']['key'] -= 31
    if change == 'budget': data['key']['pollenBudget'] = '0.01'
    if change == 'key': data['key']['id'] = 'other-key'
    if change == 'principal': data['principal'] = PRINCIPALS[1]
    eid = str(uuid4())
    with pytest.raises(HTTPException):
        flow.execute(header, consent['consent_id'], eid)
    _, state = flow.ledger.store.read(PRINCIPALS[0])
    assert state['executions'][eid]['state'] == 'RESERVED' and not persistent['calls']


def test_sql_consent_and_execution_price_commitment_are_immutable(persistent):
    flow, _, _, _, _, consent = configure(persistent)
    eid = str(uuid4())
    flow.ledger.reserve(PRINCIPALS[0], consent['consent_id'], eid)
    for kind in ('consent', 'execution'):
        revision, state = flow.ledger.store.read(PRINCIPALS[0])
        if kind == 'consent': state['consents'][consent['consent_id']]['quote']['maximum_micro_pollen'] = 1
        else: state['executions'][eid]['quote_sha256'] = '0'*64
        with pytest.raises(RuntimeError, match='immutable'):
            flow.ledger.store.cas(PRINCIPALS[0], revision, state)
    assert not persistent['calls']


def test_openai_catalog_id_shape_and_alias_preserve_pollen_units(facts):
    snapshot, _, data, pricing = facts
    data['catalog']['id'] = data['catalog'].pop('name')
    quote = pricing(snapshot)
    assert quote['maximum_micro_pollen'] == 30000
    assert quote['catalog_model_id'] == CANONICAL_MODEL
    assert quote['catalog_publisher'] == 'Black Forest Labs'
    assert snapshot['model'] == 'kontext'


@pytest.mark.parametrize('field,value', [
    ('id', 'different/model'), ('aliases', []), ('supported_endpoints', None),
    ('supported_endpoints', ['/v1/images/generations']), ('health', None),
    ('health', {'status': 'degraded'}), ('health', {'status': 'down'}),
    ('health', {'status': 'unknown'}),
])
def test_incompatible_catalog_metadata_fails_closed(facts, field, value):
    snapshot, _, data, pricing = facts
    data['catalog'][field] = value
    with pytest.raises(HTTPException) as exc:
        pricing(snapshot)
    assert exc.value.status_code == 503


@pytest.mark.parametrize('left,right,expected', [
    ('kontext', CANONICAL_MODEL, True), (CANONICAL_MODEL, 'kontext', True),
    (CANONICAL_MODEL, CANONICAL_MODEL, True), ('unknown', 'unknown', False),
    ('kontext', 'other/kontext', False),
])
def test_only_reviewed_alias_equivalence_is_allowed(left, right, expected):
    assert same_reviewed_model(left, right) is expected


def test_canonical_config_preserves_exact_consent_model_at_dispatch(persistent, monkeypatch):
    monkeypatch.setenv('POLLINATIONS_IMAGE_EDIT_MODEL', CANONICAL_MODEL)
    flow, header, _, _, _, consent = configure(persistent)
    frozen = deepcopy(consent['snapshot'])
    assert frozen['model'] == 'kontext'
    flow.execute(header, consent['consent_id'], str(uuid4()))
    assert len(persistent['calls']) == 1  # Existing provider fixture asserts exact 'kontext'.
    assert consent['snapshot'] == frozen


@pytest.mark.parametrize('expiry', [float('nan'), float('inf'), True])
def test_invalid_consent_expiry_never_reaches_pricing(expiry):
    def forbidden(_):
        pytest.fail('Pricing must not run for invalid consent')
    ledger = Ledger(pricing=forbidden, clock=lambda: 1000)
    with pytest.raises(HTTPException) as exc:
        ledger.consent(PRINCIPALS[0], {}, 1, expiry)
    assert exc.value.status_code == 400


@pytest.mark.parametrize('expiry', [float('nan'), float('inf'), 'future'])
def test_invalid_quote_expiry_never_mutates_ledger(facts, expiry):
    snapshot, _, _, _ = facts
    ledger = Ledger(pricing=lambda _: {'maximum_micro_pollen': 1, 'includes_all_charges': True,
        'basis': 'OFFLINE', 'expires_at': expiry}, clock=lambda: 1000)
    with pytest.raises(HTTPException) as exc:
        ledger.consent(PRINCIPALS[0], snapshot, 1, 1100)
    assert exc.value.status_code == 409
