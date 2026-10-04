"""Canonical content_jobs lifecycle contract.

Keep this list aligned with the latest Supabase content_jobs status constraint.
Runtime modules may use literal comparisons for readability, while contract tests
ensure those values cannot drift outside this authoritative set.
"""

from __future__ import annotations

CONTENT_JOB_STATUSES = frozenset({
    "NEW",
    "SCORING",
    "SCORED",
    "SELECTED",
    "BACKLOG",
    "ARCHIVED",
    "GENERATING",
    "READY_FOR_REVIEW",
    "APPROVED",
    "ASSET_QUEUED",
    "ASSET_GENERATING",
    "ASSET_READY",
    "ASSET_FAILED",
    "AUDIO_GENERATING",
    "AUDIO_READY",
    "AUDIO_FAILED",
    "FINAL_RENDERING",
    "RENDERING",
    "READY_TO_PUBLISH",
    "PUBLISHING",
    "PUBLISHED",
    "GENERATION_FAILED",
    "RENDER_FAILED",
    "PUBLISH_FAILED",
    "CANCELLED",
})

FAILED_CONTENT_JOB_STATUSES = frozenset({
    "GENERATION_FAILED",
    "ASSET_FAILED",
    "AUDIO_FAILED",
    "RENDER_FAILED",
    "PUBLISH_FAILED",
})

TERMINAL_CONTENT_JOB_STATUSES = frozenset({
    "ARCHIVED",
    "CANCELLED",
    "PUBLISHED",
    *FAILED_CONTENT_JOB_STATUSES,
})

BLOCKER_MESSAGES = {
    "GENERATION_FAILED": "Generation failed",
    "ASSET_FAILED": "Asset generation failed",
    "AUDIO_FAILED": "Audio generation failed",
    "RENDER_FAILED": "Render failed",
    "PUBLISH_FAILED": "Publish failed",
}


def is_content_job_status(value: object) -> bool:
    return isinstance(value, str) and value in CONTENT_JOB_STATUSES
