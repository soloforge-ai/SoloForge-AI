"""Offline contract tests for canonical Content Factory job statuses.

These tests exercise only pure state definitions; no DB, network, or providers.
"""

from __future__ import annotations

import pytest

from backend.asset_forge.backend.content_state import (
    BLOCKER_MESSAGES,
    CONTENT_JOB_STATUSES,
    FAILED_CONTENT_JOB_STATUSES,
    TERMINAL_CONTENT_JOB_STATUSES,
    is_content_job_status,
)


EXPECTED_STATUSES = frozenset({
    "NEW", "SCORING", "SCORED", "SELECTED", "BACKLOG", "ARCHIVED",
    "GENERATING", "READY_FOR_REVIEW", "APPROVED", "ASSET_QUEUED",
    "ASSET_GENERATING", "ASSET_READY", "ASSET_FAILED",
    "AUDIO_GENERATING", "AUDIO_READY", "AUDIO_FAILED",
    "FINAL_RENDERING", "RENDERING", "READY_TO_PUBLISH",
    "PUBLISHING", "PUBLISHED", "GENERATION_FAILED",
    "RENDER_FAILED", "PUBLISH_FAILED",
})

EXPECTED_FAILURES = frozenset({
    "GENERATION_FAILED", "ASSET_FAILED", "AUDIO_FAILED",
    "RENDER_FAILED", "PUBLISH_FAILED",
})


def test_canonical_status_set_is_frozen_and_complete() -> None:
    assert isinstance(CONTENT_JOB_STATUSES, frozenset)
    assert CONTENT_JOB_STATUSES == EXPECTED_STATUSES


@pytest.mark.parametrize("status", sorted(EXPECTED_STATUSES))
def test_every_canonical_status_is_accepted(status: str) -> None:
    assert is_content_job_status(status) is True


@pytest.mark.parametrize(
    "invalid",
    [
        None, False, True, 0, 1, 1.0, b"NEW", [], {}, "",
        "new", " NEW", "NEW ", "UNKNOWN", "READY_TO_PUBLISHING",
    ],
)
def test_invalid_or_non_string_status_is_rejected(invalid: object) -> None:
    assert is_content_job_status(invalid) is False


def test_failed_statuses_are_exactly_the_expected_subset() -> None:
    assert isinstance(FAILED_CONTENT_JOB_STATUSES, frozenset)
    assert FAILED_CONTENT_JOB_STATUSES == EXPECTED_FAILURES
    assert FAILED_CONTENT_JOB_STATUSES <= CONTENT_JOB_STATUSES


def test_terminal_statuses_include_archive_publish_and_all_failures() -> None:
    assert isinstance(TERMINAL_CONTENT_JOB_STATUSES, frozenset)
    assert TERMINAL_CONTENT_JOB_STATUSES == (
        EXPECTED_FAILURES | {"ARCHIVED", "PUBLISHED"}
    )
    assert TERMINAL_CONTENT_JOB_STATUSES <= CONTENT_JOB_STATUSES
    assert "PUBLISHING" not in TERMINAL_CONTENT_JOB_STATUSES
    assert "READY_TO_PUBLISH" not in TERMINAL_CONTENT_JOB_STATUSES


def test_every_failed_status_has_a_nonempty_blocker_message() -> None:
    assert set(BLOCKER_MESSAGES) == EXPECTED_FAILURES
    assert all(
        isinstance(message, str) and message.strip()
        for message in BLOCKER_MESSAGES.values()
    )
