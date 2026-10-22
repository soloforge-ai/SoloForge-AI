"""Disposable PostgreSQL integration checks. Never point at production.

Run only when SOLOFORGE_DISPOSABLE_PG_TEST=1 and the CI service database is present.
No provider, wallet, generation, or publishing calls.
"""
import concurrent.futures
import os
import uuid

import pytest

if os.environ.get('SOLOFORGE_DISPOSABLE_PG_TEST') != '1':
    pytest.skip('Disposable PostgreSQL test is explicitly disabled', allow_module_level=True)

psycopg = pytest.importorskip('psycopg')
from backend.owner_binding_postgres import PostgresAtomicBindingStore
from backend.owner_provider_binding import BindingRejected, CredentialMetadata, VerifiedIdentity

DSN = os.environ.get('SOLOFORGE_DISPOSABLE_PG_DSN', '')
if not DSN or 'localhost' not in DSN and '127.0.0.1' not in DSN:
    pytest.fail('Integration DSN must point to a local disposable PostgreSQL service', pytrace=False)


def connect():
    return psycopg.connect(DSN, connect_timeout=3)


@pytest.fixture
def owner():
    return str(uuid.uuid4())


def identity(owner, account='provider-A'):
    return VerifiedIdentity(owner, account, 'trusted-app-A')


def key(name, account='provider-A', expiry=200):
    return CredentialMetadata(name, account, 'trusted-app-A', True, expiry)


def recorded(owner):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT provider_account_id, internal_app_key_id FROM public.owner_provider_bindings WHERE owner_user_id=%s::uuid', (owner,))
            binding = cur.fetchone()
            cur.execute('SELECT provider_key_id FROM public.owner_provider_key_rotations WHERE owner_user_id=%s::uuid ORDER BY provider_key_id', (owner,))
            keys = [row[0] for row in cur.fetchall()]
    return binding, keys


def test_atomic_and_idempotent_rotation(owner):
    store = PostgresAtomicBindingStore(connect)
    for name in ('key-a', 'key-b', 'key-b'):
        store.verify_and_record(identity(owner), key(name), authenticated_owner_id=owner, now=100)
    assert recorded(owner) == (('provider-A', 'trusted-app-A'), ['key-a', 'key-b'])


def test_concurrent_rotation_same_owner(owner):
    store = PostgresAtomicBindingStore(connect)
    def rotate(n):
        store.verify_and_record(identity(owner), key(f'key-{n % 4}'), authenticated_owner_id=owner, now=100)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(rotate, range(24)))
    assert recorded(owner) == (('provider-A', 'trusted-app-A'), [f'key-{i}' for i in range(4)])


def test_concurrent_competing_owner_identity_fail_closed(owner):
    store = PostgresAtomicBindingStore(connect)
    def attempt(account):
        try:
            store.verify_and_record(identity(owner, account), key(account, account), authenticated_owner_id=owner, now=100)
            return True
        except BindingRejected:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ('provider-A', 'provider-B')))
    assert sorted(outcomes) == [False, True]
    binding, keys = recorded(owner)
    assert binding[0] in ('provider-A', 'provider-B')
    assert keys == [binding[0]]


def test_rollback_on_immutable_identity_mismatch(owner):
    store = PostgresAtomicBindingStore(connect)
    store.verify_and_record(identity(owner), key('initial'), authenticated_owner_id=owner, now=100)
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity(owner, 'attacker'), key('bad', 'attacker'), authenticated_owner_id=owner, now=100)
    assert recorded(owner) == (('provider-A', 'trusted-app-A'), ['initial'])


def test_fail_closed_invalid_owner_expiry_and_database_outage(owner):
    store = PostgresAtomicBindingStore(connect)
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity(owner), key('invalid'), authenticated_owner_id=str(uuid.uuid4()), now=100)
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity(owner), key('expired', expiry=99), authenticated_owner_id=owner, now=100)
    assert recorded(owner) == (None, [])
    unavailable = PostgresAtomicBindingStore(lambda: psycopg.connect('host=127.0.0.1 port=1 dbname=missing connect_timeout=1'))
    with pytest.raises(psycopg.OperationalError):
        unavailable.verify_and_record(identity(owner), key('no-db'), authenticated_owner_id=owner, now=100)
    assert recorded(owner) == (None, [])
