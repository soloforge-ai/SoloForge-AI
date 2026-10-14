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


def test_model_mismatch_rejected():
    with pytest.raises(GrantVerificationError):
        verify_effective_grant(USER, key(), client_id=APP, requested_model="text")


def test_missing_app_identity_rejected():
    with pytest.raises(GrantVerificationError):
        verify_effective_grant(USER, key(byopApp=None), client_id=APP)


def test_http_revoked_denied(monkeypatch):
    import io
    import urllib.error
    from backend import pollinations_grant_validation as validation

    def revoked(*args, **kwargs):
        raise urllib.error.HTTPError(validation.KEY_INFO_URL, 401, "revoked", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(validation.urllib.request, "urlopen", revoked)
    with pytest.raises(GrantVerificationError):
        validation._get_json(validation.KEY_INFO_URL, "synthetic-token")


def test_callback_fail_closed_and_success_without_provider_network(monkeypatch):
    import time
    from fastapi import HTTPException
    from backend import pollinations_oauth_router as router_module
    from backend.pollinations_oauth import PollinationsOAuthConfig

    config = PollinationsOAuthConfig(client_id=APP, redirect_uri="https://example.invalid/callback")
    monkeypatch.setattr(router_module.PollinationsOAuthConfig, "from_env", lambda: config)
    monkeypatch.setattr(router_module, "exchange_authorization_code",
                        lambda *args, **kwargs: {"access_token": "synthetic-token", "expires_in": 3600})
    observed = []
    monkeypatch.setattr(router_module, "verify_provider_token",
                        lambda token, *, client_id: observed.append((token, client_id)))
    monkeypatch.setattr(router_module, "_persist_session", lambda *args: None)
    monkeypatch.setattr(router_module, "_supabase_config", lambda: None)
    state = "synthetic-state"
    router_module._transactions[state] = router_module._OAuthTransaction("verifier", time.time())
    try:
        response = router_module.pollinations_callback(code="code", state=state, oauth_state=state)
        assert response.status_code == 302
        assert observed == [("synthetic-token", APP)]
    finally:
        router_module._transactions.pop(state, None)
        router_module._sessions.clear()


def test_callback_missing_expiry_never_persists(monkeypatch):
    import time
    from fastapi import HTTPException
    from backend import pollinations_oauth_router as router_module
    from backend.pollinations_oauth import PollinationsOAuthConfig

    config = PollinationsOAuthConfig(client_id=APP, redirect_uri="https://example.invalid/callback")
    monkeypatch.setattr(router_module.PollinationsOAuthConfig, "from_env", lambda: config)
    monkeypatch.setattr(router_module, "exchange_authorization_code",
                        lambda *args, **kwargs: {"access_token": "synthetic-token"})
    monkeypatch.setattr(router_module, "verify_provider_token",
                        lambda *args, **kwargs: pytest.fail("must not query provider with invalid expiry"))
    monkeypatch.setattr(router_module, "_persist_session",
                        lambda *args: pytest.fail("must not persist invalid session"))
    state = "synthetic-missing-expiry"
    router_module._transactions[state] = router_module._OAuthTransaction("verifier", time.time())
    try:
        with pytest.raises(HTTPException) as exc:
            router_module.pollinations_callback(code="code", state=state, oauth_state=state)
        assert exc.value.status_code == 502
    finally:
        router_module._transactions.pop(state, None)


def test_callback_provider_verification_failure_never_persists(monkeypatch):
    import time
    from fastapi import HTTPException
    from backend import pollinations_oauth_router as router_module
    from backend.pollinations_oauth import PollinationsOAuthConfig

    config = PollinationsOAuthConfig(client_id=APP, redirect_uri="https://example.invalid/callback")
    monkeypatch.setattr(router_module.PollinationsOAuthConfig, "from_env", lambda: config)
    monkeypatch.setattr(router_module, "exchange_authorization_code",
                        lambda *args, **kwargs: {"access_token": "synthetic-token", "expires_in": 3600})
    def deny(*args, **kwargs):
        raise GrantVerificationError("synthetic revoked key")
    monkeypatch.setattr(router_module, "verify_provider_token", deny)
    monkeypatch.setattr(router_module, "_persist_session",
                        lambda *args: pytest.fail("must not persist invalid session"))
    state = "synthetic-revoked"
    router_module._transactions[state] = router_module._OAuthTransaction("verifier", time.time())
    try:
        with pytest.raises(HTTPException) as exc:
            router_module.pollinations_callback(code="code", state=state, oauth_state=state)
        assert exc.value.status_code == 502
    finally:
        router_module._transactions.pop(state, None)
