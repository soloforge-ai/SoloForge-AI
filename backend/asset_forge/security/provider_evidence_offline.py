"""Offline provider-evidence verification adapter. NO NETWORK OR PROVIDER CALLS.

A production issuer MUST independently authenticate Pollinations responses and
supply its own trusted key; this module never trusts a caller-provided key.
No live issuance or wallet spending is enabled by this adapter.
"""
from dataclasses import dataclass
from hashlib import sha256
import hmac
import json

class EvidenceRejected(ValueError):
    pass

@dataclass(frozen=True)
class VerifiedEvidence:
    kind: str
    owner_id: str
    session_id: str
    subject_id: str
    provider_request_id: str
    authorization_id: str
    outcome: str
    pollen: str
    digest: str

def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def verify_offline_fixture(envelope: dict, *, trusted_test_key: bytes,
                           expected_kind: str, expected_owner: str,
                           expected_session: str, expected_subject: str,
                           expected_provider_request: str,
                           expected_authorization: str) -> VerifiedEvidence:
    """Test-only verifier. Never accept signing keys from an envelope."""
    if not trusted_test_key or len(trusted_test_key) < 32:
        raise EvidenceRejected("trusted fixture key required")
    if set(envelope) != {"payload", "signature"} or not isinstance(envelope["payload"], dict):
        raise EvidenceRejected("malformed envelope")
    payload = envelope["payload"]
    required = {"kind", "owner_id", "session_id", "subject_id",
                "provider_request_id", "authorization_id", "outcome", "pollen"}
    if set(payload) != required:
        raise EvidenceRejected("unexpected or missing evidence fields")
    if not isinstance(envelope["signature"], str):
        raise EvidenceRejected("invalid signature")
    body = canonical(payload)
    expected = hmac.digest(trusted_test_key, body, "sha256")
    try:
        supplied = bytes.fromhex(envelope["signature"])
    except ValueError as exc:
        raise EvidenceRejected("invalid signature encoding") from exc
    if not hmac.compare_digest(expected, supplied):
        raise EvidenceRejected("evidence integrity failed")
    fields = {
        "kind": expected_kind, "owner_id": expected_owner,
        "session_id": expected_session, "subject_id": expected_subject,
        "provider_request_id": expected_provider_request,
        "authorization_id": expected_authorization,
    }
    if any(payload[k] != v or not isinstance(payload[k], str) or not v for k, v in fields.items()):
        raise EvidenceRejected("evidence binding mismatch")
    if payload["outcome"] not in {"SUCCEEDED", "FAILED_CONFIRMED"}:
        raise EvidenceRejected("ambiguous or unsupported outcome")
    from decimal import Decimal, InvalidOperation
    try:
        value = Decimal(payload["pollen"])
    except (InvalidOperation, TypeError):
        raise EvidenceRejected("invalid pollen") from None
    if not value.is_finite() or value < 0:
        raise EvidenceRejected("invalid pollen")
    return VerifiedEvidence(**payload, digest=sha256(body).hexdigest())
