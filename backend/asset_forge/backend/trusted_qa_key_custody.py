"""QA signing custody boundary: non-exportable signing only, no runtime wiring.

Supabase Vault is encrypted secret storage, NOT non-exportable signing. A
deployment must supply an independently authorized signing service and a
verifier backed by trusted key metadata. No key bytes may cross this boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .trusted_qa_internal_identity import InternalPrincipal, SERVICE, ISSUER, AUDIENCE

@dataclass(frozen=True)
class KeyMetadata:
    key_id: str
    algorithm: str
    state: str
    not_before: int
    not_after: int

class NonExportableSigner(Protocol):
    def metadata(self) -> KeyMetadata: ...
    def sign(self, payload: bytes, *, key_id: str) -> bytes: ...

def sign_qa_evidence(*, principal: object, signer: NonExportableSigner | None,
                     payload: object, now: int) -> tuple[str, bytes] | None:
    """Offline adapter only. Does not grant execution or issue QA receipts."""
    if (type(principal) is not InternalPrincipal or principal.service != SERVICE
            or principal.issuer != ISSUER or principal.audience != AUDIENCE
            or type(now) is not int or principal.expires_at <= now
            or principal.expires_at > now + 300 or signer is None
            or type(payload) is not bytes or not payload or len(payload) > 65536):
        return None
    try:
        key = signer.metadata()
        if (type(key) is not KeyMetadata or not key.key_id or len(key.key_id) > 128
                or key.algorithm != "Ed25519" or key.state != "ACTIVE"
                or type(key.not_before) is not int or type(key.not_after) is not int
                or not key.not_before <= now < key.not_after):
            return None
        signature = signer.sign(payload, key_id=key.key_id)
        if type(signature) is not bytes or len(signature) != 64:
            return None
        return key.key_id, signature
    except Exception:
        return None

class SupabaseVaultSigningAdapter:
    """Explicitly unsupported: Vault can return decrypted secrets to SQL callers."""
    def metadata(self) -> KeyMetadata:
        raise RuntimeError("Vault is not a non-exportable signing service")
    def sign(self, payload: bytes, *, key_id: str) -> bytes:
        raise RuntimeError("Vault is not a non-exportable signing service")
