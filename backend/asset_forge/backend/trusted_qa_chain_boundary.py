"""Unwired, fail-closed trusted QA chain authorization boundary.

An authority must be constructed by an authenticated internal server, not by
HTTP request data. No production authority, key manager or gateway is provided.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any, Protocol
from backend.asset_forge.backend.trusted_qa_issuer import verify_trusted_chain

class ChainAuthority(Protocol):
    def authenticated_internal_caller(self) -> bool: ...
    def load_chain(self, route: str, ids: tuple[str, ...]) -> Mapping[str, Any]: ...
    def read_immutable_artifact(self, ref: str) -> bytes: ...
    def claim_chain_atomic(self, *, claim_id: str, job_id: str,
                           revision_id: str, route: str,
                           evidence_ids: tuple[str, ...]) -> bool: ...

def authorize_chain_once(*, authority: ChainAuthority | None,
                         attestations: Any, route: Any,
                         claim_id: Any, evaluated_at: Any) -> str:
    """No execution permission is returned; PASS only means QA claim recorded.

    Production safety depends on an unimplemented authenticated authority that
    atomically binds its verification snapshot to the DB transaction.
    """
    if authority is None or not isinstance(claim_id, str) or not claim_id.strip():
        return "BLOCKED"
    try:
        if authority.authenticated_internal_caller() is not True:
            return "BLOCKED"
        if verify_trusted_chain(authority=authority, attestations=attestations,
                                route=route, evaluated_at=evaluated_at) != "PASS":
            return "BLOCKED"
        ids=tuple(a["envelope"]["evidence_id"] for a in attestations)
        jobs={a["envelope"]["job_id"] for a in attestations}
        revisions={a["envelope"]["revision_id"] for a in attestations}
        if len(jobs)!=1 or len(revisions)!=1:
            return "BLOCKED"
        return "PASS" if authority.claim_chain_atomic(
            claim_id=claim_id,job_id=next(iter(jobs)),
            revision_id=next(iter(revisions)),route=route,
            evidence_ids=ids) is True else "BLOCKED"
    except Exception:
        return "BLOCKED"
