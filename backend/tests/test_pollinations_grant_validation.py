"""Offline-only synthetic tests: no provider network, wallet, or generation calls."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.pollinations_grant_validation import (
    GrantVerificationError,
    strict_expires_in,
    verify_effective_grant,
)

APP = "synthetic-app"
USER = {"sub": "provider-sub"}
FUTURE = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


def key(**overrides):
    payload = {
        "id": "synthetic-key",
        "valid": True,
        "type": "secret",
        "expiresIn": 3600,
        "expiresAt": FUTURE,
        "permissions": {"models": ["image"], "account": None},
        "pollenBudget": 2.5,
        "questPollenOnly": True,
        "userId": "provider-owner",
        "byopApp": {"clientKeyId": APP, "name": "Synthetic", "appUser": "app-owner"},
    }
    payload.update(overrides)
    return payload


def test_limited_budget_metadata_only():
    result = verify_effective_grant(USER, key(), client_id=APP, requested_model="image",
                                    max_remaining_budget=3, require_quest_only=True)
    assert result["status"] == "METADATA_VERIFIED_SPENDING_BLOCKED"


@pytest.mark.parametrize("overrides", [
    {"pollenBudget": None},
    {"pollenBudget": 0},
    {"pollenBudget": -1},
    {"pollenBudget": float("nan")},
    {"permissions": {"models": ["text"]}},
    {"permissions": {"models": None}},
    {"expiresIn": 0},
    {"expiresIn": -1},
    {"expiresAt": "2000-01-01T00:00:00Z"},
    {"valid": False},
    {"type": "publishable"},
    {"userId": None},
    {"byopApp": {"clientKeyId": "wrong"}},
    {"questPollenOnly": False},
])
def test_reject_bad_grants(overrides):
    with pytest.raises(GrantVerificationError):
        verify_effective_grant(USER, key(**overrides), client_id=APP,
                               requested_model="image", require_quest_only=True)


@pytest.mark.parametrize("value", [None, 0, -1, "3600", True, 1.5, 366 * 86400])
def test_reject_bad_oauth_expiry(value):
    with pytest.raises(GrantVerificationError):
        strict_expires_in({"expires_in": value})


def test_missing_subject():
    with pytest.raises(GrantVerificationError):
        verify_effective_grant({}, key(), client_id=APP)


def test_key_budget_above_local_policy():
    with pytest.raises(GrantVerificationError):
        verify_effective_grant(USER, key(), client_id=APP, max_remaining_budget=1)


def test_strict_expiry_valid():
    assert strict_expires_in({"expires_in": 3600}) == 3600
