"""P0-B1 offline evidence verification; NOT an issuer, authorization gate, or I/O path.

The trusted snapshot MUST be constructed by a future authenticated server issuer.
Passing a user-controlled snapshot does not establish trust. Fail closed by default.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

STAGES = ("CONTENT", "GROUNDING", "VISUAL", "AUDIO", "VIDEO_RENDER", "FINAL_QA")
RESULTS = frozenset(("PASS", "FAIL", "REVIEW_REQUIRED", "BLOCKED", "STALE"))
SHA256 = re.compile(r"^[a-f0-9]{64}$")
# Conservative v1 dependency graph. Non-video routes do not require audio/render.
DEPS = {
    "CONTENT": (),
    "GROUNDING": ("CONTENT",),
    "VISUAL": ("CONTENT", "GROUNDING"),
    "AUDIO": ("CONTENT",),
    "VIDEO_RENDER": ("VISUAL", "AUDIO"),
    "FINAL_QA": ("CONTENT", "GROUNDING", "VISUAL"),
}
FIELDS = frozenset(("schema_version", "evidence_id", "job_id", "stage", "revision_id",
                    "input_sha256", "output_sha256", "artifact_ref", "validator_version",
                    "result", "reviewer_id", "reviewed_at", "dependency_evidence_ids"))


def _valid(e: Any) -> bool:
    if not isinstance(e, Mapping) or set(e) != FIELDS or e.get("schema_version") != "1.0":
        return False
    if e.get("stage") not in STAGES or e.get("result") not in RESULTS:
        return False
    for key in ("evidence_id", "job_id", "revision_id", "artifact_ref",
                "validator_version", "reviewer_id"):
        if not isinstance(e.get(key), str) or not e[key].strip():
            return False
    if not all(isinstance(e.get(k), str) and SHA256.fullmatch(e[k])
               for k in ("input_sha256", "output_sha256")):
        return False
    deps = e.get("dependency_evidence_ids")
    if not isinstance(deps, list) or any(not isinstance(x, str) or not x.strip() for x in deps):
        return False
    if len(deps) != len(set(deps)):
        return False
    try:
        date = datetime.fromisoformat(e["reviewed_at"].replace("Z", "+00:00"))
        if date.tzinfo is None or date.utcoffset() is None:
            return False
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def verify_evidence(evidence: Any, *, trusted_snapshot: Any,
                    upstream: Any = ()) -> str:
    """Return PASS or BLOCKED. No signature, identity, hash calculation, or I/O.

    trusted_snapshot is a server-derived immutable expectation, NOT client input.
    Keys: job_id, revision_id, stage, input_sha256, output_sha256,
    artifact_ref, reviewer_id, evidence_id; plus required_stages (list).
    upstream contains separately trusted, already verified PASS envelopes.
    """
    if not _valid(evidence) or not isinstance(trusted_snapshot, Mapping):
        return "BLOCKED"
    expected = ("job_id", "revision_id", "stage", "input_sha256", "output_sha256",
                "artifact_ref", "reviewer_id", "evidence_id")
    if any(not isinstance(trusted_snapshot.get(k), str)
           or evidence[k] != trusted_snapshot[k] for k in expected):
        return "BLOCKED"
    if evidence["result"] != "PASS":
        return "BLOCKED"
    required = trusted_snapshot.get("required_stages")
    if not isinstance(required, list) or any(s not in STAGES for s in required):
        return "BLOCKED"
    if len(required) != len(set(required)):
        return "BLOCKED"
    stage = evidence["stage"]
    if set(required) != set(DEPS[stage]) and not (
        stage == "FINAL_QA" and set(required) == set(DEPS[stage]) | {"AUDIO", "VIDEO_RENDER"}
    ):
        return "BLOCKED"
    if not isinstance(upstream, (tuple, list)) or any(not _valid(x) for x in upstream):
        return "BLOCKED"
    by_stage = {}
    for item in upstream:
        if (item["result"] != "PASS" or item["job_id"] != evidence["job_id"]
                or item["revision_id"] != evidence["revision_id"]
                or item["evidence_id"] == evidence["evidence_id"]
                or item["stage"] in by_stage):
            return "BLOCKED"
        by_stage[item["stage"]] = item
    if set(by_stage) != set(required):
        return "BLOCKED"
    if set(evidence["dependency_evidence_ids"]) != {x["evidence_id"] for x in upstream}:
        return "BLOCKED"
    # A future issuer must attest that upstream envelopes were authenticated.
    trusted_upstream_ids = trusted_snapshot.get("verified_upstream_evidence_ids")
    if not isinstance(trusted_upstream_ids, list) or set(trusted_upstream_ids) != set(evidence["dependency_evidence_ids"]):
        return "BLOCKED"
    return "PASS"
