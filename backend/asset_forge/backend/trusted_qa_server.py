"""P0-B4 fail-closed server integration preparation (NOT wired to HTTP/runtime).

This verifier accepts independently trusted server-side dependencies. No client
input is a trusted principal, grant, artifact, key, snapshot or replay ledger.
The service is deliberately non-operational without explicitly provisioned
trusted backends; no Supabase/provider I/O is performed by this module.
"""
from __future__ import annotations
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any, Protocol
from backend.asset_forge.backend.offline_qa_issuance import (
    verify_attestation, verify_offline_chain,
)
from backend.asset_forge.backend.reviewer_authorization import authorize_reviewer

class TrustedQABackend(Protocol):
    def load_context(self, evidence_id: str) -> Mapping[str, Any]: ...
    def read_immutable_artifact(self, artifact_ref: str) -> bytes: ...
    def claim_once(self, evidence_id: str, claim_id: str, job_id: str,
                   revision_id: str, stage: str, principal_id: str) -> bool: ...
    def audit_decision(self, evidence_id: str, decision: str) -> None: ...


def verify_and_claim(*, backend: TrustedQABackend | None, attestation: Any,
                     claim_id: Any) -> str:
    """Verify a single attestation then claim atomically via a trusted backend.

    Requires external authentication, key custody, immutable storage and
    durable transactional audit. Not a production-ready issuer or runtime gate.
    """
    if backend is None or not isinstance(attestation, Mapping):
        return "BLOCKED"
    env = attestation.get("envelope")
    if not isinstance(env, Mapping) or not isinstance(claim_id, str) or not claim_id.strip():
        return "BLOCKED"
    eid = env.get("evidence_id")
    if not isinstance(eid, str) or not eid.strip():
        return "BLOCKED"
    try:
        ctx = backend.load_context(eid)
        if not isinstance(ctx, Mapping):
            return "BLOCKED"
        required = ("trusted_principal", "trusted_grant", "trusted_target",
                    "evaluated_at", "trusted_keys", "expected_envelope",
                    "input_artifact_ref", "input_sha256",
                    "output_artifact_ref", "output_sha256")
        if any(k not in ctx for k in required):
            return "BLOCKED"
        expected = ctx["expected_envelope"]
        if not isinstance(expected, Mapping) or dict(env) != dict(expected):
            return "BLOCKED"
        if verify_attestation(attestation=attestation,
                              trusted_keys=ctx["trusted_keys"]) != "PASS":
            return "BLOCKED"
        if authorize_reviewer(trusted_principal=ctx["trusted_principal"],
                              trusted_grant=ctx["trusted_grant"],
                              trusted_target=ctx["trusted_target"],
                              evaluated_at=ctx["evaluated_at"]) != "PASS":
            return "BLOCKED"
        if env["reviewer_id"] != ctx["trusted_principal"]["principal_id"]:
            return "BLOCKED"
        for ref_key, hash_key, envelope_hash in (
            ("input_artifact_ref", "input_sha256", "input_sha256"),
            ("output_artifact_ref", "output_sha256", "output_sha256"),
        ):
            ref, expected_hash = ctx[ref_key], ctx[hash_key]
            if not isinstance(ref, str) or not ref or not isinstance(expected_hash, str):
                return "BLOCKED"
            data = backend.read_immutable_artifact(ref)
            if type(data) is not bytes:
                return "BLOCKED"
            digest = hashlib.sha256(data).hexdigest()
            if not hmac.compare_digest(digest, expected_hash) or not hmac.compare_digest(digest, env[envelope_hash]):
                return "BLOCKED"
        if not backend.claim_once(eid, claim_id, env["job_id"], env["revision_id"],
                                  env["stage"], env["reviewer_id"]):
            return "BLOCKED"
        # The durable claim RPC must audit in the SAME transaction. No additional
        # I/O or provider execution is authorized by this success.
        return "PASS"
    except (Exception):
        # Fail closed, including storage outages, revocation races, and errors.
        return "BLOCKED"
