from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from backend.asset_forge.backend import soloforge_session


@pytest.fixture(autouse=True)
def session_secret(monkeypatch):
    monkeypatch.setenv(
        "SOLOFORGE_SESSION_SECRET",
        "test-only-soloforge-session-secret-0123456789",
    )
    monkeypatch.setenv("SOLOFORGE_SESSION_TTL_SECONDS", "3600")


def test_issue_and_validate_soloforge_session() -> None:
    session = soloforge_session.issue_session()

    assert session.expires_at > int(time.time())
    assert soloforge_session.validate_session_token(session.session_id) is True
    assert soloforge_session.validate_session_token(session.session_id + "tampered") is False


def test_require_rejects_missing_or_provider_token() -> None:
    for authorization in (None, "Bearer provider-session"):
        with pytest.raises(HTTPException) as exc:
            soloforge_session.require_soloforge_session(authorization)
        assert exc.value.status_code == 401


def test_exchange_requires_valid_legacy_session(monkeypatch) -> None:
    monkeypatch.setattr(
        soloforge_session,
        "get_pollinations_access_token_from_authorization",
        lambda authorization: (
            "provider-secret" if authorization == "Bearer legacy-session" else None
        ),
    )

    with pytest.raises(HTTPException) as exc:
        soloforge_session.exchange_legacy_session("Bearer invalid")
    assert exc.value.status_code == 401

    result = soloforge_session.exchange_legacy_session("Bearer legacy-session")

    assert result["session_type"] == "soloforge"
    assert result["session_token"] != "legacy-session"
    assert "provider-secret" not in str(result)
    assert soloforge_session.validate_session_token(result["session_token"]) is True


def test_status_never_exposes_provider_credential() -> None:
    session = soloforge_session.issue_session()
    result = soloforge_session.soloforge_session_status(
        f"Bearer {session.session_id}"
    )

    assert result == {"authenticated": True, "session_type": "soloforge"}


def test_refresh_rotates_valid_app_session_without_provider(monkeypatch) -> None:
    original = soloforge_session.issue_session()

    monkeypatch.setattr(
        soloforge_session,
        "get_pollinations_access_token_from_authorization",
        lambda _: (_ for _ in ()).throw(
            AssertionError("refresh must not call provider auth")
        ),
    )

    refreshed = soloforge_session.refresh_soloforge_session(
        f"Bearer {original.session_id}"
    )

    assert refreshed["session_type"] == "soloforge"
    assert refreshed["session_token"] != original.session_id
    assert soloforge_session.validate_session_token(refreshed["session_token"]) is True


def test_refresh_rejects_invalid_app_session() -> None:
    with pytest.raises(HTTPException) as exc:
        soloforge_session.refresh_soloforge_session("Bearer invalid")
    assert exc.value.status_code == 401
