from __future__ import annotations

import io
import json
import time
import urllib.error

import pytest
from fastapi import HTTPException

from backend.asset_forge.backend import soloforge_session as auth

OWNER = "72112ead-d399-4a40-aa51-ee17811cb10d"
ANONYMOUS = "00000000-0000-4000-8000-000000000001"


@pytest.fixture(autouse=True)
def owner_configuration(monkeypatch):
    monkeypatch.setenv("SOLOFORGE_SESSION_SECRET", "test-only-soloforge-session-secret-0123456789")
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", OWNER)
    monkeypatch.setenv("SOLOFORGE_SESSION_TTL_SECONDS", "3600")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
    monkeypatch.delenv("SOLOFORGE_SESSION_NOT_BEFORE", raising=False)


def _auth_user(
    monkeypatch, user_id=OWNER, providers=None, anonymous=False,
    valid_bearer="supabase-github-token",
):
    payload = {
        "id": user_id,
        "is_anonymous": anonymous,
        "app_metadata": {"providers": providers if providers is not None else ["github"]},
    }

    def fake_urlopen(request, timeout):
        if request.get_header("Authorization") != f"Bearer {valid_bearer}":
            raise urllib.error.HTTPError(request.full_url, 401, "invalid bearer", {}, None)
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(auth.urllib.request, "urlopen", fake_urlopen)


def test_verified_github_owner_bootstraps_and_persists_app_session(monkeypatch):
    _auth_user(monkeypatch)
    result = auth.bootstrap_first_party_session("Bearer supabase-github-token")
    assert result["identity_provider"] == "supabase_github"
    assert auth.validate_session_token(result["session_token"])
    assert auth.soloforge_session_status(
        f"Bearer {result['session_token']}"
    )["authenticated"]
    assert "supabase-github-token" not in str(result)
    assert auth.refresh_soloforge_session(
        "Bearer supabase-github-token"
    )["session_token"] != result["session_token"]
    with pytest.raises(HTTPException) as stolen:
        auth.refresh_soloforge_session(f"Bearer {result['session_token']}")
    assert stolen.value.status_code == 403


@pytest.mark.parametrize(
    "user_id,providers,anonymous",
    [
        (ANONYMOUS, ["anonymous"], True),
        (ANONYMOUS, ["github"], False),
        (OWNER, ["anonymous"], True),
        (OWNER, ["email"], False),
    ],
)
def test_anonymous_other_user_or_wrong_provider_cannot_bootstrap(
    monkeypatch, user_id, providers, anonymous
):
    _auth_user(monkeypatch, user_id, providers, anonymous, valid_bearer="untrusted-supabase-token")
    with pytest.raises(HTTPException) as exc:
        auth.bootstrap_first_party_session("Bearer untrusted-supabase-token")
    assert exc.value.status_code == 403


def test_missing_or_invalid_identity_cannot_bootstrap(monkeypatch):
    with pytest.raises(HTTPException) as missing:
        auth.bootstrap_first_party_session(None)
    assert missing.value.status_code == 401
    monkeypatch.setattr(
        auth.urllib.request, "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(urllib.error.URLError("invalid")),
    )
    with pytest.raises(HTTPException) as invalid:
        auth.bootstrap_first_party_session("Bearer invalid")
    assert invalid.value.status_code == 403


def test_old_unbound_session_and_provider_exchange_are_rejected():
    old_payload = f"v1.{int(time.time()) + 3600}.legacy-nonce"
    old_token = f"{old_payload}.{auth._sign(old_payload)}"
    assert not auth.validate_session_token(old_token)
    with pytest.raises(HTTPException) as exc:
        auth.require_soloforge_session(f"Bearer {old_token}")
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exchange:
        auth.exchange_legacy_session("Bearer provider-session")
    assert exchange.value.status_code == 410


def test_owner_token_cannot_survive_revocation_or_owner_change(monkeypatch):
    session = auth.issue_session(OWNER)
    assert auth.validate_session_token(session.session_id)
    assert not auth.validate_session_token(session.session_id + "tampered")
    monkeypatch.setenv("SOLOFORGE_SESSION_NOT_BEFORE", str(int(time.time()) + 1))
    assert not auth.validate_session_token(session.session_id)
    monkeypatch.delenv("SOLOFORGE_SESSION_NOT_BEFORE")
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", ANONYMOUS)
    assert not auth.validate_session_token(session.session_id)


def test_missing_owner_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("SOLOFORGE_OWNER_USER_ID", "")
    with pytest.raises(ValueError):
        auth.issue_session(OWNER)
    assert not auth.validate_session_token("v2.untrusted")


def test_final_video_requires_app_session(monkeypatch):
    from backend.asset_forge import main

    def signed_url(job_id: str, expires_in: int) -> str:
        assert (job_id, expires_in) == ("job-123", 600)
        return "https://example.invalid/signed-video"

    monkeypatch.setattr(main, "create_signed_video_url", signed_url)
    for authorization in (None, "Bearer invalid"):
        with pytest.raises(HTTPException) as exc:
            main.download_final_content_video("job-123", authorization)
        assert exc.value.status_code == 401
    session = auth.issue_session(OWNER)
    response = main.download_final_content_video(
        "job-123", f"Bearer {session.session_id}"
    )
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.invalid/signed-video"
