"""Pure offline fake-store tests: no network, credentials or provider calls."""
import pytest

from backend.owner_provider_binding import (
    BindingRejected, CredentialMetadata, VerifiedIdentity,
    establish_binding, rotate_credential,
)


class FakeStore:
    def __init__(self):
        self.bindings = {}
        self.rotations = []

    def load(self, owner_user_id):
        return self.bindings.get(owner_user_id)

    def insert_once(self, identity):
        if identity.owner_user_id in self.bindings:
            raise BindingRejected("Duplicate owner")
        self.bindings[identity.owner_user_id] = identity

    def record_rotation(self, owner_user_id, key_id):
        self.rotations.append((owner_user_id, key_id))


OWNER = VerifiedIdentity("solo-owner", "provider-account", "internal-app-id")


def key(**changes):
    fields = dict(key_id="key-v2", provider_account_id="provider-account",
                  internal_app_key_id="internal-app-id", valid=True, expires_at=200)
    fields.update(changes)
    return CredentialMetadata(**fields)


def test_persistent_identity_survives_key_rotation():
    store = FakeStore()
    establish_binding(store, OWNER, authenticated_owner_id="solo-owner")
    rotate_credential(store, authenticated_owner_id="solo-owner", verified_key=key(), now=100)
    rotate_credential(store, authenticated_owner_id="solo-owner", verified_key=key(key_id="key-v3"), now=100)
    assert store.load("solo-owner") == OWNER
    assert store.rotations == [("solo-owner", "key-v2"), ("solo-owner", "key-v3")]


@pytest.mark.parametrize("candidate", [
    key(provider_account_id="other-account"), key(internal_app_key_id="other-app"),
    key(valid=False), key(expires_at=100), key(expires_at=99),
    key(key_id=""),
])
def test_invalid_rotation_denied_without_mutation(candidate):
    store = FakeStore()
    establish_binding(store, OWNER, authenticated_owner_id="solo-owner")
    with pytest.raises(BindingRejected):
        rotate_credential(store, authenticated_owner_id="solo-owner", verified_key=candidate, now=100)
    assert store.rotations == []


def test_other_owner_cannot_rotate():
    store = FakeStore()
    establish_binding(store, OWNER, authenticated_owner_id="solo-owner")
    with pytest.raises(BindingRejected):
        rotate_credential(store, authenticated_owner_id="intruder", verified_key=key(), now=100)
    assert store.rotations == []


def test_existing_binding_cannot_be_reassigned():
    store = FakeStore()
    establish_binding(store, OWNER, authenticated_owner_id="solo-owner")
    with pytest.raises(BindingRejected):
        establish_binding(store, VerifiedIdentity("solo-owner", "other-account", "internal-app-id"),
                          authenticated_owner_id="solo-owner")
    assert store.load("solo-owner") == OWNER


def test_initial_binding_requires_authenticated_owner():
    store = FakeStore()
    with pytest.raises(BindingRejected):
        establish_binding(store, OWNER, authenticated_owner_id="intruder")
    assert store.bindings == {}
