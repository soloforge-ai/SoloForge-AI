"""Read-only Pollinations SK preflight. No key creation or billable generation.

The caller MUST verify SoloForge Owner V2 separately before treating the result
as an owner-authorized binding. A provider subject alone is not owner proof.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

USERINFO_URL = "https://enter.pollinations.ai/api/oauth/userinfo"
TIMEOUT_SECONDS = 8


class SKState(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ACCOUNT_BALANCE_EXHAUSTED = "ACCOUNT_BALANCE_EXHAUSTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SKPreflight:
    state: SKState
    provider_subject: str | None = None
    reason: str = ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a bearer credential to a redirected origin.
        return None


def provider_get(url: str, token: str) -> tuple[int, dict]:
    if url not in (USERINFO_URL, "https://gen.pollinations.ai/account/balance"):
        return 0, {}
    request = urllib.request.Request(url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read(32768).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, UnicodeError):
        return 0, {}


def _userinfo(token: str) -> tuple[int, dict]:
    return provider_get(USERINFO_URL, token)


def inspect_sk(
    *,
    token: str,
    expires_at: float,
    expected_subject: str | None,
    owner_authorized: bool,
    budget_confirmed: bool = False,
    now: float | None = None,
) -> SKPreflight:
    """Fail closed until identity, owner and budget evidence are established.

    budget_confirmed is reserved for a separately authenticated, key-specific
    read-only budget check. Account balance must not be substituted for it.
    """
    if not owner_authorized or not expected_subject:
        return SKPreflight(SKState.UNKNOWN, reason="owner_binding_unverified")
    if not token.startswith("sk_"):
        return SKPreflight(SKState.UNKNOWN, reason="credential_invalid")
    if expires_at <= (time.time() if now is None else now):
        return SKPreflight(SKState.EXPIRED, reason="local_expiry")
    status, payload = _userinfo(token)
    if status in (401, 403):
        return SKPreflight(SKState.REVOKED, reason="provider_rejected")
    if status != 200 or not isinstance(payload, dict):
        return SKPreflight(SKState.UNKNOWN, reason="provider_unavailable")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        return SKPreflight(SKState.UNKNOWN, reason="provider_subject_missing")
    if subject != expected_subject:
        return SKPreflight(SKState.UNKNOWN, reason="provider_subject_mismatch")
    if not budget_confirmed:
        return SKPreflight(SKState.UNKNOWN, provider_subject=subject, reason="key_budget_unverified")
    return SKPreflight(SKState.VALID, provider_subject=subject)


def verify_identity(token: str, expires_at: float, expected_subject: str | None) -> dict:
    """Identity-only reverification. Pending is allowed; balance is not identity proof."""
    result = {"verification_status": "PENDING_VERIFICATION", "verification_outcome": "UNKNOWN",
              "provider_ownership_verified": False, "spending_authorized": False}
    if not isinstance(token, str) or not token.startswith("sk_"):
        return {**result, "verification_outcome": "REJECTED", "reason": "credential_invalid"}
    if expires_at <= time.time():
        return {**result, "reason": "credential_expired"}
    status, payload = _userinfo(token)
    subject = payload.get("sub") if isinstance(payload, dict) else None
    if status in (401, 403):
        return {**result, "verification_outcome": "REJECTED", "reason": "provider_rejected"}
    if status != 200 or not isinstance(subject, str) or not subject.strip() or len(subject) > 512 or "sk_" in subject or "Bearer " in subject:
        return {**result, "reason": "provider_identity_unavailable"}
    if not expected_subject:
        return {**result, "reason": "independent_account_evidence_required", "provider_subject": subject}
    if subject != expected_subject:
        return {**result, "verification_outcome": "REJECTED", "reason": "provider_subject_mismatch"}
    return {**result, "verification_status": "VERIFIED", "verification_outcome": "VERIFIED", "provider_ownership_verified": True,
            "provider_subject": subject}
