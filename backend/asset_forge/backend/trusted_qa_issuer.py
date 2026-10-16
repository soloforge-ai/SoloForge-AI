"""P0-B4 trusted QA issuer and key lifecycle CONTRACT; offline/unwired.

Keys, principal, grants, snapshots, bytes, route and time must come from
independently authenticated server authorities. No live key manager is provided.
"""
from __future__ import annotations
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any, Protocol
from backend.asset_forge.backend.offline_qa_issuance import (
    issue_attestation, verify_attestation, verify_offline_chain, canonical_bytes,
)
from backend.asset_forge.backend.revision_dependency_verification import GRAPHS
from backend.asset_forge.backend.reviewer_authorization import authorize_reviewer

class TrustedIssuerAuthority(Protocol):
    def load_issuance(self, evidence_id: str) -> Mapping[str, Any]: ...
    def read_immutable_artifact(self, ref: str) -> bytes: ...
    def active_signing_key(self) -> tuple[str, bytes]: ...

def _digest(backend: Any, ref: Any, expected: Any) -> bool:
    if not isinstance(ref, str) or not ref or not isinstance(expected, str):
        return False
    data = backend.read_immutable_artifact(ref)
    return type(data) is bytes and hmac.compare_digest(hashlib.sha256(data).hexdigest(), expected)

def issue_trusted(*, authority: TrustedIssuerAuthority | None, evidence_id: Any) -> dict | None:
    """Produce a signed evidence envelope only after server-sourced validation."""
    if authority is None or not isinstance(evidence_id, str) or not evidence_id:
        return None
    try:
        ctx = authority.load_issuance(evidence_id)
        if not isinstance(ctx, Mapping):
            return None
        needed = ("envelope", "principal", "grant", "target", "evaluated_at",
                  "input_ref", "output_ref")
        if any(k not in ctx for k in needed):
            return None
        env = ctx["envelope"]
        if not isinstance(env, Mapping) or env.get("evidence_id") != evidence_id:
            return None
        if not _digest(authority, ctx["input_ref"], env.get("input_sha256")):
            return None
        if not _digest(authority, ctx["output_ref"], env.get("output_sha256")):
            return None
        if env.get("artifact_ref") != ctx["output_ref"]:
            return None
        key_id, key = authority.active_signing_key()
        return issue_attestation(envelope=env, trusted_principal=ctx["principal"],
                                 trusted_grant=ctx["grant"], trusted_target=ctx["target"],
                                 evaluated_at=ctx["evaluated_at"], key_id=key_id, signing_key=key)
    except Exception:
        return None

def verify_with_lifecycle(*, attestation: Any, trusted_key_records: Any,
                          evaluated_at: Any) -> str:
    """Require trusted key status and UTC validity before HMAC verification."""
    from backend.asset_forge.backend.reviewer_authorization import _utc
    if not isinstance(attestation, Mapping) or not isinstance(trusted_key_records, Mapping):
        return "BLOCKED"
    kid = attestation.get("key_id")
    record = trusted_key_records.get(kid) if isinstance(kid, str) else None
    if not isinstance(record, Mapping) or set(record) != {"key", "status", "not_before", "not_after"}:
        return "BLOCKED"
    if record["status"] not in ("ACTIVE", "VERIFY_ONLY"):
        return "BLOCKED"
    now, start, end = (_utc(v) for v in (evaluated_at, record["not_before"], record["not_after"]))
    if now is None or start is None or end is None or not start <= now < end:
        return "BLOCKED"
    return verify_attestation(attestation=attestation, trusted_keys={kid: record["key"]})

def verify_trusted_chain(*, authority: Any, attestations: Any, route: Any,
                         evaluated_at: Any) -> str:
    """Full route validation using independently loaded server context and bytes.

    Read-only; cannot authorize FINAL_QA or reserve replay IDs atomically.
    """
    if authority is None or route not in GRAPHS or not isinstance(attestations, (list, tuple)):
        return "BLOCKED"
    if len(attestations) != len(GRAPHS[route]):
        return "BLOCKED"
    try:
        ids = [a["envelope"]["evidence_id"] for a in attestations]
        if any(not isinstance(eid, str) for eid in ids) or len(set(ids)) != len(ids):
            return "BLOCKED"
        ctx = authority.load_chain(route, tuple(ids))
        if not isinstance(ctx, Mapping) or set(ctx) != {
            "snapshots", "revision", "key_records", "reviewers", "artifacts", "consumed_ids"
        }:
            return "BLOCKED"
        if set(ctx["snapshots"]) != set(ids) or set(ctx["reviewers"]) != set(ids):
            return "BLOCKED"
        trusted_keys = {}
        for signed in attestations:
            eid = signed["envelope"]["evidence_id"]
            if verify_with_lifecycle(attestation=signed,
                                     trusted_key_records=ctx["key_records"],
                                     evaluated_at=evaluated_at) != "PASS":
                return "BLOCKED"
            reviewer = ctx["reviewers"][eid]
            if not isinstance(reviewer, Mapping) or set(reviewer) != {"principal", "grant", "target"}:
                return "BLOCKED"
            if authorize_reviewer(trusted_principal=reviewer["principal"],
                                  trusted_grant=reviewer["grant"],
                                  trusted_target=reviewer["target"],
                                  evaluated_at=evaluated_at) != "PASS":
                return "BLOCKED"
            if reviewer["principal"]["principal_id"] != signed["envelope"]["reviewer_id"]:
                return "BLOCKED"
            record = ctx["key_records"][signed["key_id"]]
            trusted_keys[signed["key_id"]] = record["key"]
        # The offline chain validator verifies all signatures, output hashes,
        # revision and ordered route dependencies. Input bytes are separately
        # verified against each authoritative snapshot below.
        for eid in ids:
            snap = ctx["snapshots"][eid]
            refs = ctx["artifacts"].get(eid)
            if not isinstance(refs, Mapping) or set(refs) != {"input_ref", "output_ref"}:
                return "BLOCKED"
            if refs["output_ref"] != snap["artifact_ref"]:
                return "BLOCKED"
            if not _digest(authority, refs["input_ref"], snap["input_sha256"]):
                return "BLOCKED"
            if not _digest(authority, refs["output_ref"], snap["output_sha256"]):
                return "BLOCKED"
        outputs = {eid: authority.read_immutable_artifact(ctx["artifacts"][eid]["output_ref"])
                   for eid in ids}
        return verify_offline_chain(attestations=attestations, route=route,
                                    trusted_snapshots=ctx["snapshots"],
                                    trusted_revision=ctx["revision"],
                                    trusted_artifacts=outputs,
                                    trusted_keys=trusted_keys,
                                    consumed_evidence_ids=ctx["consumed_ids"])
    except Exception:
        return "BLOCKED"
