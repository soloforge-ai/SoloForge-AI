"""Fail-closed owner/provider binding and secret-key rotation contract.

This module never reads secret-key values or grants spending permission.
The caller must supply independently verified identities from trusted backends.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BindingRejected(ValueError):
    """Identity evidence is missing, mismatched, or not trustworthy."""


@dataclass(frozen=True)
class VerifiedIdentity:
    owner_user_id: str
    provider_account_id: str
    internal_app_key_id: str


@dataclass(frozen=True)
class CredentialMetadata:
    key_id: str
    provider_account_id: str
    internal_app_key_id: str
    valid: bool
    expires_at: int


class BindingStore(Protocol):
    def load(self, owner_user_id: str) -> VerifiedIdentity | None: ...
    def insert_once(self, identity: VerifiedIdentity) -> None: ...
    def record_rotation(self, owner_user_id: str, key_id: str) -> None: ...


def _nonempty(*values: str) -> bool:
    return all(isinstance(v, str) and bool(v.strip()) and v == v.strip() for v in values)


def establish_binding(store: BindingStore, identity: VerifiedIdentity, *,
                      authenticated_owner_id: str) -> None:
    """First binding requires an independently authenticated SoloForge principal.

    `identity` must come from trusted provider metadata, never from the client.
    Storage must enforce unique owner and immutable provider/app identity.
    """
    if not _nonempty(identity.owner_user_id, identity.provider_account_id,
                     identity.internal_app_key_id, authenticated_owner_id):
        raise BindingRejected("Missing verified identity")
    if identity.owner_user_id != authenticated_owner_id:
        raise BindingRejected("SoloForge owner mismatch")
    existing = store.load(authenticated_owner_id)
    if existing is not None:
        if existing != identity:
            raise BindingRejected("Existing binding cannot be overwritten")
        return
    store.insert_once(identity)


def rotate_credential(store: BindingStore, *, authenticated_owner_id: str,
                      verified_key: CredentialMetadata, now: int) -> None:
    """Accept only fresh provider-verified key metadata for the same account/app.

    This records a key identifier, not a secret; it does NOT authorize spending.
    The caller must separately verify expiry, revocation, models and budget
    before any manual QA dispatch. No fallback to a server-side sk_ key.
    """
    binding = store.load(authenticated_owner_id)
    if binding is None or not _nonempty(authenticated_owner_id, verified_key.key_id,
                                        verified_key.provider_account_id,
                                        verified_key.internal_app_key_id):
        raise BindingRejected("No trusted owner binding")
    if (binding.owner_user_id != authenticated_owner_id or
            verified_key.provider_account_id != binding.provider_account_id or
            verified_key.internal_app_key_id != binding.internal_app_key_id):
        raise BindingRejected("Provider owner/app mismatch")
    if type(now) is not int or type(verified_key.expires_at) is not int or not verified_key.valid or verified_key.expires_at <= now:
        raise BindingRejected("Credential expired or revoked")
    store.record_rotation(authenticated_owner_id, verified_key.key_id)
