"""Fail-closed production trust admission policy for P0-B4.

This module does NOT authenticate network callers, access a KMS, or permit QA
execution. An application must separately implement an authenticated gateway,
KMS custody, immutable storage and transaction-bound revalidation.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

REQUIRED = frozenset({
    "caller_authenticated", "caller_service", "audience", "issuer",
    "key_source", "key_state", "key_algorithm", "key_id",
    "transactional_revalidation", "snapshot_locked",
    "artifact_bytes_revalidated", "revocation_locked", "atomic_audit",
})

def production_trust_admitted(proof: Any) -> bool:
    """Reject mock, caller-supplied or incomplete trust claims.

    This is an offline *policy check*, not proof of provenance. No runtime
    code may treat a caller-controlled mapping as an authenticated proof.
    """
    if not isinstance(proof, Mapping) or set(proof) != REQUIRED:
        return False
    # Deliberately refuse all mappings: until the concrete internal gateway
    # supplies non-forgeable attestation, boolean assertions are not evidence.
    return False

def production_qa_authorized(*, identity: Any = None, keys: Any = None,
                             transaction: Any = None) -> bool:
    """Production gate stays closed independent of fixture injection."""
    return False
