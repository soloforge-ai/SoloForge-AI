"""P0-B3.1 offline reviewer authorization policy.

Pure policy evaluation only. The trusted principal, authorization grant,
review target, and evaluation time MUST be supplied by a future authenticated
server authority, never copied from a submitted evidence envelope. A PASS
does not issue evidence, authenticate a session, or authorize execution.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

_FIELDS_PRINCIPAL = frozenset({"principal_id", "authenticated", "session_expires_at"})
_FIELDS_GRANT = frozenset({
    "principal_id", "job_id", "allowed_stages", "revision_id",
    "expires_at", "revoked",
})
_FIELDS_TARGET = frozenset({"job_id", "stage", "revision_id"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_STAGES = frozenset({
    "CONTENT", "GROUNDING", "VISUAL", "AUDIO", "VIDEO_RENDER", "FINAL_QA",
})


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _id(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def authorize_reviewer(
    *, trusted_principal: Any, trusted_grant: Any,
    trusted_target: Any, evaluated_at: Any,
) -> str:
    """Return PASS or BLOCKED; never use PASS as a production permission.

    All four inputs are trusted test fixtures or future server-derived values.
    No request-supplied reviewer_id, JWT, OAuth token, role or wallet is parsed.
    """
    if not all(isinstance(x, Mapping) for x in (
        trusted_principal, trusted_grant, trusted_target
    )):
        return "BLOCKED"
    if (set(trusted_principal) != _FIELDS_PRINCIPAL
            or set(trusted_grant) != _FIELDS_GRANT
            or set(trusted_target) != _FIELDS_TARGET):
        return "BLOCKED"
    if not all(_id(x) for x in (
        trusted_principal["principal_id"], trusted_grant["principal_id"],
        trusted_grant["job_id"], trusted_grant["revision_id"],
        trusted_target["job_id"], trusted_target["revision_id"],
    )):
        return "BLOCKED"
    if trusted_principal["authenticated"] is not True:
        return "BLOCKED"
    if type(trusted_grant["revoked"]) is not bool or trusted_grant["revoked"]:
        return "BLOCKED"
    stages = trusted_grant["allowed_stages"]
    if (not isinstance(stages, (tuple, list)) or not stages
            or any(not isinstance(s, str) or s not in _STAGES for s in stages)
            or len(set(stages)) != len(stages)):
        return "BLOCKED"
    if (not isinstance(trusted_target["stage"], str)
            or trusted_target["stage"] not in _STAGES):
        return "BLOCKED"
    now = _utc(evaluated_at)
    session_expiry = _utc(trusted_principal["session_expires_at"])
    grant_expiry = _utc(trusted_grant["expires_at"])
    if now is None or session_expiry is None or grant_expiry is None:
        return "BLOCKED"
    if now >= session_expiry or now >= grant_expiry:
        return "BLOCKED"
    if trusted_principal["principal_id"] != trusted_grant["principal_id"]:
        return "BLOCKED"
    if trusted_grant["job_id"] != trusted_target["job_id"]:
        return "BLOCKED"
    if trusted_grant["revision_id"] != trusted_target["revision_id"]:
        return "BLOCKED"
    if trusted_target["stage"] not in stages:
        return "BLOCKED"
    return "PASS"
