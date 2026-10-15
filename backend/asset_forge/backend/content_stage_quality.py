"""P0-A advisory-only offline quality classification; no I/O, no execution or publish gates."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

VALID_STAGES = ("CONTENT", "GROUNDING", "VISUAL", "AUDIO", "VIDEO_RENDER", "FINAL_QA")
VALID_RESULTS = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED", "BLOCKED", "STALE"})

@dataclass(frozen=True)
class StageAssessment:
    stage: str
    result: str
    reason_codes: tuple[str, ...]
    return_stage: str | None

    def __post_init__(self) -> None:
        if self.stage not in VALID_STAGES or self.result not in VALID_RESULTS:
            raise ValueError("Invalid stage quality assessment")

    def as_dict(self) -> dict[str, Any]:
        return {"stage": self.stage, "result": self.result,
                "reason_codes": list(self.reason_codes), "return_stage": self.return_stage}

def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}

def _value(value: Any) -> str:
    return str(value or "").strip().upper()

def assess_stage(job: Mapping[str, Any], stage: str,
                 *, evidence: Mapping[str, Any] | None = None,
                 visual_evidence: Mapping[str, Any] | None = None) -> StageAssessment:
    """Classify legacy metadata. Evidence is caller-supplied and NOT authenticated."""
    if stage not in VALID_STAGES:
        raise ValueError("Unknown stage")
    package = _mapping(job.get("content_package"))
    route = _value(package.get("pipeline_route"))
    cert = _mapping(evidence)

    # Known failures and dependencies cannot be overridden by a supplied certificate.
    if stage == "VISUAL" and route == "VIDEO" and (
        _value(package.get("asset_provider")) == "LOCAL_TEMPLATE"
        or _value(package.get("asset_mode")) == "DETERMINISTIC_FALLBACK"
    ):
        return StageAssessment(stage, "FAIL", ("VIDEO_LOCAL_TEMPLATE_FALLBACK",), "VISUAL")
    if stage == "CONTENT":
        semantic = _value(_mapping(package.get("semantic_fidelity")).get("status"))
        if semantic in {"FAIL", "STALE"}:
            return StageAssessment(stage, semantic, ("SEMANTIC_" + semantic,), "CONTENT")
    if stage in {"VIDEO_RENDER", "AUDIO"} and route != "VIDEO":
        return StageAssessment(stage, "BLOCKED", ("STAGE_NOT_APPLICABLE",), None)
    # A render decision must include explicit matching upstream visual evidence.
    if stage == "VIDEO_RENDER" and assess_stage(job, "VISUAL", evidence=visual_evidence).result != "PASS":
        return StageAssessment(stage, "BLOCKED", ("UPSTREAM_VISUAL_NOT_PASSED",), "VISUAL")

    # Known hard failures and absent assets take precedence over caller-supplied evidence.
    if stage == "GROUNDING":
        if _value(package.get("product_grounding_status")) in {"BLOCKED", "FAILED", "FAIL"}:
            return StageAssessment(stage, "FAIL", ("GROUNDING_FAILED",), "GROUNDING")
        if not _mapping(package.get("product_grounding")) and not package.get("product_grounding_status"):
            return StageAssessment(stage, "BLOCKED", ("GROUNDING_EVIDENCE_MISSING",), "GROUNDING")
    if stage == "VISUAL":
        if _value(_mapping(package.get("asset_quality_gate")).get("result")) in {"FAIL", "FAILED"}:
            return StageAssessment(stage, "FAIL", ("ASSET_GATE_FAILED",), "VISUAL")
        if not package.get("asset_storage_path"):
            return StageAssessment(stage, "BLOCKED", ("VISUAL_ASSET_MISSING",), "VISUAL")
    if stage == "AUDIO":
        if _value(job.get("audio_status")) in {"FAILED", "FAIL"}:
            return StageAssessment(stage, "FAIL", ("AUDIO_FAILED",), "AUDIO")
        if not job.get("audio_storage_path"):
            return StageAssessment(stage, "BLOCKED", ("AUDIO_ASSET_MISSING",), "AUDIO")
    if stage == "VIDEO_RENDER" and _value(_mapping(job.get("render_qa")).get("status")) != "PASS":
        return StageAssessment(stage, "BLOCKED", ("RENDER_TECHNICAL_QA_MISSING",), "VIDEO_RENDER")
    if stage == "CONTENT" and not _value(_mapping(package.get("semantic_fidelity")).get("status")):
        return StageAssessment(stage, "BLOCKED", ("SEMANTIC_EVIDENCE_MISSING",), "CONTENT")
    # No trusted chain of stage attestations exists in P0-A; never claim final PASS.
    if stage == "FINAL_QA":
        return StageAssessment(stage, "BLOCKED", ("TRUSTED_STAGE_CHAIN_MISSING",), "FINAL_QA")

    if cert:
        if _value(cert.get("stage")) != stage:
            return StageAssessment(stage, "BLOCKED", ("EVIDENCE_STAGE_MISMATCH",), stage)
        if not cert.get("input_sha256") or not cert.get("output_sha256"):
            return StageAssessment(stage, "BLOCKED", ("EVIDENCE_HASH_MISSING",), stage)
        if (cert.get("input_sha256") != job.get("current_input_sha256")
                or cert.get("output_sha256") != job.get("current_output_sha256")):
            return StageAssessment(stage, "STALE", ("REVISION_MISMATCH",), stage)
        decision = _value(cert.get("result"))
        if decision not in VALID_RESULTS:
            return StageAssessment(stage, "BLOCKED", ("INVALID_EVIDENCE_RESULT",), stage)
        if decision == "PASS" and not cert.get("validator_version"):
            return StageAssessment(stage, "BLOCKED", ("VALIDATOR_VERSION_MISSING",), stage)
        if decision == "PASS" and stage in {"VISUAL", "VIDEO_RENDER", "FINAL_QA"} and not cert.get("reviewer"):
            return StageAssessment(stage, "REVIEW_REQUIRED", ("MANUAL_REVIEW_MISSING",), stage)
        reasons = cert.get("reason_codes", ())
        if not isinstance(reasons, (list, tuple)) or any(
            not isinstance(code, str) or not code.strip() for code in reasons
        ):
            return StageAssessment(stage, "BLOCKED", ("INVALID_REASON_CODES",), stage)
        return StageAssessment(stage, decision, tuple(reasons),
                               stage if decision != "PASS" else None)

    if stage == "CONTENT":
        if not _value(_mapping(package.get("semantic_fidelity")).get("status")):
            return StageAssessment(stage, "BLOCKED", ("SEMANTIC_EVIDENCE_MISSING",), "CONTENT")
        return StageAssessment(stage, "REVIEW_REQUIRED", ("CONTENT_MANUAL_QA_MISSING",), "CONTENT")
    if stage == "GROUNDING":
        if not _mapping(package.get("product_grounding")) and not package.get("product_grounding_status"):
            return StageAssessment(stage, "BLOCKED", ("GROUNDING_EVIDENCE_MISSING",), "GROUNDING")
        if _value(package.get("product_grounding_status")) in {"BLOCKED", "FAILED"}:
            return StageAssessment(stage, "FAIL", ("GROUNDING_FAILED",), "GROUNDING")
        return StageAssessment(stage, "REVIEW_REQUIRED", ("GROUNDING_QA_MISSING",), "GROUNDING")
    if stage == "VISUAL":
        gate = _mapping(package.get("asset_quality_gate"))
        if _value(gate.get("result")) == "FAIL":
            return StageAssessment(stage, "FAIL", ("ASSET_GATE_FAILED",), "VISUAL")
        if not package.get("asset_storage_path"):
            return StageAssessment(stage, "BLOCKED", ("VISUAL_ASSET_MISSING",), "VISUAL")
        return StageAssessment(stage, "REVIEW_REQUIRED", ("VISUAL_GLYPH_LAYOUT_QA_MISSING",), "VISUAL")
    if stage == "AUDIO":
        if _value(job.get("audio_status")) == "FAILED":
            return StageAssessment(stage, "FAIL", ("AUDIO_FAILED",), "AUDIO")
        if not job.get("audio_storage_path"):
            return StageAssessment(stage, "BLOCKED", ("AUDIO_ASSET_MISSING",), "AUDIO")
        return StageAssessment(stage, "REVIEW_REQUIRED", ("AUDIO_CONTENT_QA_MISSING",), "AUDIO")
    if stage == "VIDEO_RENDER":
        if _value(_mapping(job.get("render_qa")).get("status")) != "PASS":
            return StageAssessment(stage, "BLOCKED", ("RENDER_TECHNICAL_QA_MISSING",), "VIDEO_RENDER")
        return StageAssessment(stage, "REVIEW_REQUIRED", ("PLAYBACK_SUBTITLE_QA_MISSING",), "VIDEO_RENDER")
    return StageAssessment(stage, "BLOCKED", ("FINAL_STAGE_CERTIFICATE_MISSING",), "FINAL_QA")
