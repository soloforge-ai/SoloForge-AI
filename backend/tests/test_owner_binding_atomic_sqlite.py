"""Disposable SQLite integration tests: no network or production DB."""
import sqlite3
import time
import pytest
from backend.owner_binding_sqlite import LocalAtomicBindingStore
from backend.owner_provider_binding import VerifiedIdentity, CredentialMetadata, BindingRejected


def test_atomic_rotation_and_immutable_owner(tmp_path):
    path = tmp_path / 'binding.db'
    store = LocalAtomicBindingStore(str(path))
    identity = VerifiedIdentity('owner', 'provider', 'app')
    def key(k, account='provider', expiry=9999999999):
        return CredentialMetadata(k, account, 'app', True, expiry)
    store.verify_and_record(identity, key('old'), authenticated_owner_id='owner', now=100)
    store.verify_and_record(identity, key('new'), authenticated_owner_id='owner', now=100)
    store.verify_and_record(identity, key('new'), authenticated_owner_id='owner', now=100)
    with pytest.raises(BindingRejected):
        store.verify_and_record(VerifiedIdentity('owner', 'other', 'app'), key('bad', 'other'), authenticated_owner_id='owner', now=100)
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity, key('expired', expiry=99), authenticated_owner_id='owner', now=100)
    with pytest.raises(BindingRejected):
        store.verify_and_record(identity, key('wrong', 'other'), authenticated_owner_id='owner', now=100)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT owner_id,account_id,app_id FROM owner_bindings').fetchall() == [('owner','provider','app')]
        assert db.execute('SELECT key_id FROM key_rotations ORDER BY key_id').fetchall() == [('new',), ('old',)]


def test_failed_new_owner_does_not_persist(tmp_path):
    path = tmp_path / 'binding.db'
    store = LocalAtomicBindingStore(str(path))
    with pytest.raises(BindingRejected):
        store.verify_and_record(VerifiedIdentity('owner', 'provider', 'app'),
            CredentialMetadata('key', 'different', 'app', True, 9999999999),
            authenticated_owner_id='owner', now=100)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM owner_bindings').fetchone()[0] == 0


def test_missing_db_path_denied():
    with pytest.raises(BindingRejected):
        LocalAtomicBindingStore('')
