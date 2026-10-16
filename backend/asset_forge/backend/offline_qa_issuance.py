"""P0-B3 offline QA foundation: fixture-only HMAC attestations and artifact binding.

No runtime integration, trusted key management, durable replay claims or provider I/O.
A PASS is advisory and never authorizes FINAL_QA, generation or publishing.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from typing import Any
from backend.asset_forge.backend.reviewer_authorization import authorize_reviewer
from backend.asset_forge.backend.revision_dependency_verification import GRAPHS, verify_revision_chain
from backend.asset_forge.backend.trusted_qa_evidence import SHA256, _valid

KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
SIGNED_FIELDS = frozenset(("scheme", "key_id", "envelope", "signature"))
SNAPSHOT_FIELDS = frozenset(("job_id", "revision_id", "stage", "input_sha256",
                             "output_sha256", "artifact_ref", "reviewer_id",
                             "evidence_id", "verified_upstream_evidence_ids"))


def canonical_bytes(value: Any) -> bytes | None:
    """Deterministic UTF-8 JSON; exclude floats, NaN, tuples and custom objects."""
    def valid(x: Any) -> bool:
        if x is None or type(x) in (str, int, bool):
            return True
        if type(x) is list:
            return all(valid(v) for v in x)
        if type(x) is dict:
            return all(type(k) is str and valid(v) for k, v in x.items())
        return False
    if not valid(value):
        return None
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        return None


def artifact_sha256(artifact: Any) -> str | None:
    """Hash trusted fixture bytes only; does not retrieve artifacts from storage."""
    return hashlib.sha256(artifact).hexdigest() if type(artifact) is bytes else None


def verify_artifacts(*, trusted_snapshots: Any, trusted_artifacts: Any) -> str:
    if not isinstance(trusted_snapshots, Mapping) or not isinstance(trusted_artifacts, Mapping):
        return "BLOCKED"
    if not trusted_snapshots or set(trusted_snapshots) != set(trusted_artifacts):
        return "BLOCKED"
    refs = set()
    for eid, snapshot in trusted_snapshots.items():
        if not isinstance(snapshot, Mapping) or set(snapshot) != SNAPSHOT_FIELDS:
            return "BLOCKED"
        ref = snapshot.get("artifact_ref")
        if (not isinstance(eid, str) or snapshot.get("evidence_id") != eid
                or not isinstance(ref, str) or not ref or ref in refs):
            return "BLOCKED"
        refs.add(ref)
        if any(not isinstance(snapshot.get(k), str) or not SHA256.fullmatch(snapshot[k])
               for k in ("input_sha256", "output_sha256")):
            return "BLOCKED"
        if artifact_sha256(trusted_artifacts[eid]) != snapshot["output_sha256"]:
            return "BLOCKED"
    return "PASS"


def _key(value: Any) -> bool:
    return type(value) is bytes and len(value) >= 32


def issue_attestation(*, envelope: Any, trusted_principal: Any, trusted_grant: Any,
                      trusted_target: Any, evaluated_at: Any,
                      key_id: Any, signing_key: Any) -> dict | None:
    """Sign an offline fixture only; trusted inputs must not come from request data."""
    if not _valid(envelope) or envelope["result"] != "PASS":
        return None
    if not isinstance(trusted_target, Mapping) or any(
            envelope[k] != trusted_target.get(k) for k in ("job_id", "stage", "revision_id")):
        return None
    if not isinstance(trusted_principal, Mapping) or envelope["reviewer_id"] != trusted_principal.get("principal_id"):
        return None
    if authorize_reviewer(trusted_principal=trusted_principal, trusted_grant=trusted_grant,
                          trusted_target=trusted_target, evaluated_at=evaluated_at) != "PASS":
        return None
    if not isinstance(key_id, str) or not KEY_ID.fullmatch(key_id) or not _key(signing_key):
        return None
    body = {"scheme": "HMAC-SHA256-v1", "key_id": key_id, "envelope": dict(envelope)}
    payload = canonical_bytes(body)
    if payload is None:
        return None
    return {**body, "signature": hmac.new(signing_key, payload, hashlib.sha256).hexdigest()}


def verify_attestation(*, attestation: Any, trusted_keys: Any) -> str:
    if not isinstance(attestation, Mapping) or set(attestation) != SIGNED_FIELDS:
        return "BLOCKED"
    if attestation.get("scheme") != "HMAC-SHA256-v1" or not _valid(attestation.get("envelope")):
        return "BLOCKED"
    kid = attestation.get("key_id")
    if not isinstance(kid, str) or not KEY_ID.fullmatch(kid):
        return "BLOCKED"
    if not isinstance(trusted_keys, Mapping) or not _key(trusted_keys.get(kid)):
        return "BLOCKED"
    signature = attestation.get("signature")
    if not isinstance(signature, str) or not SHA256.fullmatch(signature):
        return "BLOCKED"
    payload = canonical_bytes({k: attestation[k] for k in ("scheme", "key_id", "envelope")})
    if payload is None:
        return "BLOCKED"
    expected = hmac.new(trusted_keys[kid], payload, hashlib.sha256).hexdigest()
    return "PASS" if hmac.compare_digest(signature, expected) else "BLOCKED"


def verify_offline_chain(*, attestations: Any, route: Any, trusted_snapshots: Any,
                         trusted_revision: Any, trusted_artifacts: Any,
                         trusted_keys: Any, consumed_evidence_ids: Any) -> str:
    """Read-only replay check; atomic reservation and persistent ledger NOT implemented."""
    if not isinstance(route, str) or route not in GRAPHS:
        return "BLOCKED"
    if not isinstance(attestations, (tuple, list)) or len(attestations) != len(GRAPHS[route]):
        return "BLOCKED"
    if not isinstance(consumed_evidence_ids, (set, frozenset)) or any(
            type(x) is not str for x in consumed_evidence_ids):
        return "BLOCKED"
    evidence, seen = [], set()
    for signed in attestations:
        if verify_attestation(attestation=signed, trusted_keys=trusted_keys) != "PASS":
            return "BLOCKED"
        item = signed["envelope"]
        eid = item["evidence_id"]
        if eid in seen or eid in consumed_evidence_ids:
            return "BLOCKED"
        seen.add(eid)
        evidence.append(item)
    if verify_artifacts(trusted_snapshots=trusted_snapshots,
                        trusted_artifacts=trusted_artifacts) != "PASS":
        return "BLOCKED"
    return verify_revision_chain(evidence, route=route,
                                 trusted_snapshots=trusted_snapshots,
                                 trusted_revision=trusted_revision)


def audit_record(*, attestation: Any, decision: Any, evaluated_at: Any) -> dict | None:
    """Pure audit record fixture, not persisted or independently authenticated."""
    if decision not in ("PASS", "BLOCKED", "STALE") or not isinstance(evaluated_at, str):
        return None
    if not isinstance(attestation, Mapping) or not _valid(attestation.get("envelope")):
        return None
    env = attestation["envelope"]
    return {"evidence_id": env["evidence_id"], "job_id": env["job_id"],
            "stage": env["stage"], "revision_id": env["revision_id"],
            "reviewer_id": env["reviewer_id"], "decision": decision,
            "evaluated_at": evaluated_at}
