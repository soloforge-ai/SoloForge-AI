"""Offline security tests for Pollinations SK preflight; no provider calls."""
from unittest.mock import patch

from backend.pollinations_sk_lifecycle import SKState, inspect_sk


BASE = dict(token="sk_test_not_a_real_secret", expires_at=200, expected_subject="expected-sub", owner_authorized=True, now=100)


def test_unverified_owner_does_not_call_provider():
    with patch("backend.pollinations_sk_lifecycle._userinfo") as provider:
        result = inspect_sk(**{**BASE, "owner_authorized": False})
    assert result.state is SKState.UNKNOWN
    assert result.reason == "owner_binding_unverified"
    provider.assert_not_called()


def test_expired_does_not_call_provider():
    with patch("backend.pollinations_sk_lifecycle._userinfo") as provider:
        result = inspect_sk(**{**BASE, "expires_at": 99})
    assert result.state is SKState.EXPIRED
    provider.assert_not_called()


def test_invalid_credential_does_not_call_provider():
    with patch("backend.pollinations_sk_lifecycle._userinfo") as provider:
        result = inspect_sk(**{**BASE, "token": "bad"})
    assert result.state is SKState.UNKNOWN
    provider.assert_not_called()


def test_provider_revocation():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(401, {})):
        result = inspect_sk(**BASE)
    assert result.state is SKState.REVOKED


def test_provider_timeout_fails_closed():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(0, {})):
        result = inspect_sk(**BASE)
    assert result.state is SKState.UNKNOWN


def test_subject_mismatch_fails_closed():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(200, {"sub": "other"})):
        result = inspect_sk(**{**BASE, "budget_confirmed": True})
    assert result.state is SKState.UNKNOWN
    assert result.reason == "provider_subject_mismatch"


def test_matching_subject_without_budget_proof_fails_closed():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(200, {"sub": "expected-sub"})):
        result = inspect_sk(**BASE)
    assert result.state is SKState.UNKNOWN
    assert result.reason == "key_budget_unverified"


def test_valid_requires_all_proofs():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(200, {"sub": "expected-sub"})):
        result = inspect_sk(**{**BASE, "budget_confirmed": True})
    assert result.state is SKState.VALID


def test_missing_subject_fails_closed():
    with patch("backend.pollinations_sk_lifecycle._userinfo", return_value=(200, {})):
        result = inspect_sk(**{**BASE, "budget_confirmed": True})
    assert result.state is SKState.UNKNOWN
