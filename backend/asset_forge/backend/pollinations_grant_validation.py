"""Read-only Pollinations BYOP identity and effective-grant verification.

This module does NOT authorize spending, create allocations, or mint attestations.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone

USERINFO_URL = "https://enter.pollinations.ai/api/oauth/userinfo"
KEY_INFO_URL = "https://gen.pollinations.ai/account/key"
TIMEOUT_SECONDS = 10


class GrantVerificationError(RuntimeError):
    """Fail-closed provider metadata verification failure."""


def _get_json(url: str, token: str) -> dict:
    if not isinstance(token, str) or not token.strip():
        raise GrantVerificationError("Missing provider credential")
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise GrantVerificationError("Provider verification failed")
            raw = response.read(65537)
            if len(raw) > 65536:
                raise GrantVerificationError("Provider response too large")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GrantVerificationError("Provider verification unavailable") from exc
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise GrantVerificationError("Invalid provider verification response") from exc
    if not isinstance(payload, dict):
        raise GrantVerificationError("Invalid provider verification response")
    return payload


def strict_expires_in(payload: dict) -> int:
    value = payload.get("expires_in")
    if type(value) is not int or value <= 0 or value > 365 * 86400:
        raise GrantVerificationError("Invalid OAuth token lifetime")
    return value


def verify_effective_grant(userinfo: dict, key: dict, *, client_id: str,
                           requested_model: str | None = None,
                           max_remaining_budget: float | None = None,
                           require_quest_only: bool = False) -> dict:
    """Validate provider metadata; returned result is NOT a spending grant."""
    sub = userinfo.get("sub")
    owner = key.get("userId")
    byop = key.get("byopApp")
    if not isinstance(sub, str) or not sub.strip():
        raise GrantVerificationError("Missing provider subject")
    if not isinstance(owner, str) or not owner.strip():
        raise GrantVerificationError("Missing key owner")
    # Do not infer equality between distinct provider identifier namespaces.
    # Trusted owner-to-session attestation remains a separate, blocked gate.
    if key.get("valid") is not True or key.get("type") != "secret":
        raise GrantVerificationError("Invalid BYOP secret key")
    if not isinstance(byop, dict) or byop.get("clientKeyId") != client_id:
        raise GrantVerificationError("Wrong BYOP application")
    expiry = key.get("expiresIn")
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or expiry <= 0:
        raise GrantVerificationError("Expired or unverified key")
    expires_at = key.get("expiresAt")
    if not isinstance(expires_at, str):
        raise GrantVerificationError("Missing key expiry")
    try:
        expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expiry_time.tzinfo is None or expiry_time <= datetime.now(timezone.utc):
            raise GrantVerificationError("Expired key")
    except ValueError as exc:
        raise GrantVerificationError("Invalid key expiry") from exc
    budget = key.get("pollenBudget")
    if type(budget) not in (int, float) or not math.isfinite(budget) or budget <= 0:
        raise GrantVerificationError("Unbounded or depleted key budget")
    if max_remaining_budget is not None and budget > max_remaining_budget:
        raise GrantVerificationError("Key budget exceeds local policy")
    if require_quest_only and key.get("questPollenOnly") is not True:
        raise GrantVerificationError("Paid Pollen is not authorized")
    permissions = key.get("permissions")
    models = permissions.get("models") if isinstance(permissions, dict) else None
    if not isinstance(models, list) or not models or any(not isinstance(m, str) for m in models):
        raise GrantVerificationError("Unrestricted or invalid model permissions")
    if requested_model is not None and requested_model not in models:
        # Category expansion needs a trusted model catalog; never guess.
        raise GrantVerificationError("Model not explicitly authorized")
    return {"provider_subject": sub, "key_owner": owner, "key_id": key.get("id"),
            "budget_remaining": budget, "models": tuple(models),
            "status": "METADATA_VERIFIED_SPENDING_BLOCKED"}


def verify_provider_token(token: str, *, client_id: str) -> dict:
    return verify_effective_grant(
        _get_json(USERINFO_URL, token),
        _get_json(KEY_INFO_URL, token),
        client_id=client_id,
    )
