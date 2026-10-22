"""Offline trusted PostgreSQL adapter contract; no real DB or network."""
import pytest
from backend.owner_binding_postgres import PostgresAtomicBindingStore
from backend.owner_provider_binding import VerifiedIdentity, CredentialMetadata, BindingRejected

OWNER = '72112ead-d399-4a40-aa51-ee17811cb10d'

class FakeConnection:
    def __init__(self, db):
        self.db = db
        self.owner = dict(db.owner)
        self.keys = set(db.keys)
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, kind, *_):
        if kind is None:
            self.db.owner = self.owner
            self.db.keys = self.keys
        return False
    def cursor(self): return self
    def execute(self, sql, params):
        self.queries.append(sql)
        if 'INSERT INTO public.owner_provider_bindings' in sql:
            self.owner.setdefault(params[0], (params[1], params[2]))
        elif 'INSERT INTO public.owner_provider_key_rotations' in sql:
            self.keys.add((params[0], params[1]))
        elif 'SELECT provider_account_id' in sql:
            self.selected = self.owner.get(params[0])
        else: raise AssertionError('Unexpected SQL')
    def fetchone(self): return self.selected

class FakeDB:
    def __init__(self):
        self.owner = {}
        self.keys = set()
        self.connections = []
    def connect(self):
        c = FakeConnection(self)
        self.connections.append(c)
        return c

def key(name, account='provider', expiry=200):
    return CredentialMetadata(name, account, 'app', True, expiry)

def test_postgres_atomic_binding_rotation_and_rollback():
    db = FakeDB()
    store = PostgresAtomicBindingStore(db.connect)
    identity = VerifiedIdentity(OWNER, 'provider', 'app')
    store.verify_and_record(identity, key('one'), authenticated_owner_id=OWNER, now=100)
    store.verify_and_record(identity, key('two'), authenticated_owner_id=OWNER, now=100)
    store.verify_and_record(identity, key('two'), authenticated_owner_id=OWNER, now=100)
    assert db.owner == {OWNER: ('provider', 'app')}
    assert db.keys == {(OWNER, 'one'), (OWNER, 'two')}
    assert all('FOR UPDATE' in ' '.join(c.queries) for c in db.connections)
    with pytest.raises(BindingRejected):
        store.verify_and_record(VerifiedIdentity(OWNER, 'other', 'app'),
                                key('three', 'other'), authenticated_owner_id=OWNER, now=100)
    assert (OWNER, 'three') not in db.keys
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity, key('expired', expiry=99), authenticated_owner_id=OWNER, now=100)
    assert len(db.connections) == 4

def test_postgres_denies_missing_connection_or_owner():
    with pytest.raises(BindingRejected):
        PostgresAtomicBindingStore(None)
    db = FakeDB()
    with pytest.raises(BindingRejected):
        PostgresAtomicBindingStore(db.connect).verify_and_record(
            VerifiedIdentity(OWNER, 'provider', 'app'), key('one'),
            authenticated_owner_id='wrong', now=100)
    assert db.connections == []
