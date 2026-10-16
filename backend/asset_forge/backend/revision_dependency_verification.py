"""P0-B2 pure offline route-aware QA chain verification (advisory only).

All snapshots and route selection MUST originate from a future trusted issuer.
This module does not authenticate principals, calculate artifact hashes, perform
I/O, or authorize generation/publishing. P0-A FINAL_QA remains fail-closed.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.asset_forge.backend.trusted_qa_evidence import SHA256, _valid, verify_evidence

GRAPHS = {
    "IMAGE": {
        "CONTENT": (),
        "GROUNDING": ("CONTENT",),
        "VISUAL": ("CONTENT", "GROUNDING"),
        "FINAL_QA": ("VISUAL",),
    },
    "VIDEO": {
        "CONTENT": (),
        "GROUNDING": ("CONTENT",),
        "VISUAL": ("CONTENT", "GROUNDING"),
        "AUDIO": ("CONTENT",),
        "VIDEO_RENDER": ("VISUAL", "AUDIO"),
        "FINAL_QA": ("VIDEO_RENDER",),
    },
}
BOUND_FIELDS = ("job_id", "revision_id", "stage", "input_sha256",
                "output_sha256", "artifact_ref", "reviewer_id", "evidence_id")


def verify_revision_chain(
    evidence: Any, *, route: Any, trusted_snapshots: Any,
    trusted_revision: Any,
) -> str:
    """Return PASS, STALE, or BLOCKED; PASS is advisory, never authorization.

    trusted_snapshots: mapping evidence_id -> server-derived expected envelope
    fields, each including its verified_upstream_evidence_ids.
    trusted_revision: server-derived mapping of stage -> revision_id.
    evidence: list of envelopes forming an exact single route graph.
    Dependency IDs are canonical ordered lists matching each stage's GRAPHS
    tuple, in both evidence and trusted snapshot; reordering is BLOCKED.
    """
    if route not in GRAPHS or not isinstance(evidence, (tuple, list)):
        return "BLOCKED"
    if not isinstance(trusted_snapshots, Mapping) or not isinstance(trusted_revision, Mapping):
        return "BLOCKED"
    graph = GRAPHS[route]
    if len(evidence) != len(graph) or len(trusted_snapshots) != len(graph):
        return "BLOCKED"
    by_stage, by_id = {}, {}
    for item in evidence:
        # Reject malformed envelopes before evaluating freshness; invalid
        # hashes must never be classified as legitimate stale revisions.
        if not _valid(item):
            return "BLOCKED"
        stage, eid = item.get("stage"), item.get("evidence_id")
        if not isinstance(stage, str) or stage not in graph:
            return "BLOCKED"
        if not isinstance(eid, str) or not eid or eid in by_id or stage in by_stage:
            return "BLOCKED"
        by_id[eid], by_stage[stage] = item, item
    if set(by_stage) != set(graph) or set(by_id) != set(trusted_snapshots):
        return "BLOCKED"
    if set(trusted_revision) != set(graph):
        return "BLOCKED"
    job_ids = {x.get("job_id") for x in evidence}
    if len(job_ids) != 1:
        return "BLOCKED"
    stale = False
    for stage, deps in graph.items():
        item = by_stage[stage]
        snapshot = trusted_snapshots.get(item["evidence_id"])
        if not isinstance(snapshot, Mapping) or not all(
            isinstance(snapshot.get(k), str) for k in BOUND_FIELDS
        ):
            return "BLOCKED"
        if any(not SHA256.fullmatch(snapshot[k]) for k in
               ("input_sha256", "output_sha256")):
            return "BLOCKED"
        if snapshot["stage"] != stage or snapshot["job_id"] != item["job_id"]:
            return "BLOCKED"
        if not isinstance(trusted_revision.get(stage), str):
            return "BLOCKED"
        if item.get("revision_id") != trusted_revision[stage]:
            stale = True
        if any(item.get(k) != snapshot[k] for k in
               ("revision_id", "input_sha256", "output_sha256", "artifact_ref")):
            stale = True
        # The route graph defines canonical dependency order. Both envelope
        # and trusted snapshot must use that exact order.
        expected_ids = [by_stage[s]["evidence_id"] for s in deps]
        if (item.get("dependency_evidence_ids") != expected_ids
                or snapshot.get("verified_upstream_evidence_ids") != expected_ids):
            return "BLOCKED"
        if any(item.get(k) != snapshot[k] for k in
               ("job_id", "stage", "reviewer_id", "evidence_id")):
            return "BLOCKED"
    if stale:
        return "STALE"
    # Existing B1 validator expects its own direct stage graph; check each
    # envelope against its trusted fields without relaxing B1 constraints.
    # Route-specific graph validation above is authoritative for this offline
    # chain and deliberately does not call B1's fixed dependency graph.
    for stage, deps in graph.items():
        item = by_stage[stage]
        snapshot = trusted_snapshots[item["evidence_id"]]
        if item.get("result") != "PASS":
            return "BLOCKED"
        # Reuse B1's strict envelope shape and scalar checks through its
        # public validator for root CONTENT; downstream shapes are validated
        # by a route-aware envelope check below.
        if stage == "CONTENT":
            root_snapshot = dict(snapshot, required_stages=[],
                                 verified_upstream_evidence_ids=[])
            if verify_evidence(item, trusted_snapshot=root_snapshot) != "PASS":
                return "BLOCKED"
        if any(item[k] != snapshot[k] for k in BOUND_FIELDS):
            return "BLOCKED"
        if set(item["dependency_evidence_ids"]) != {
            by_stage[s]["evidence_id"] for s in deps
        }:
            return "BLOCKED"
    return "PASS"
