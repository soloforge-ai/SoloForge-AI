"""Owner V2 compatibility checks; no network or credentials."""
import time
from fastapi import HTTPException
from backend import soloforge_session as session
from backend import owner_v2


def test_v2_status_uses_v2_identity(monkeypatch):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    monkeypatch.setattr(owner_v2.OwnerV2, "authenticate", lambda self, auth: {"authenticated": True})
    assert session.soloforge_session_status("Bearer sf_owner_v2_test") == {"authenticated": True, "session_type": "owner_v2"}


def test_v2_status_denies_invalid_token(monkeypatch):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    def reject(self, auth):
        raise owner_v2.Unauthorized("invalid")
    monkeypatch.setattr(owner_v2.OwnerV2, "authenticate", reject)
    assert session.soloforge_session_status("Bearer invalid") == {"authenticated": False, "session_type": "owner_v2"}


def test_v2_status_fails_closed_when_database_unavailable(monkeypatch):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    def unavailable(self, auth):
        raise owner_v2.Unavailable("down")
    monkeypatch.setattr(owner_v2.OwnerV2, "authenticate", unavailable)
    try:
        session.soloforge_session_status("Bearer sf_owner_v2_test")
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("must fail closed")


def test_v2_bootstrap_returns_absolute_expiry(monkeypatch):
    monkeypatch.setenv("OWNER_V2_AUTH_ENABLED", "true")
    monkeypatch.setattr(session, "_supabase_owner_id", lambda auth: session._VERIFIED_OWNER_USER_ID)
    monkeypatch.setattr(owner_v2.OwnerV2, "github_session", lambda self, uid: {"session_token": "sf_owner_v2_test", "expires_in": 3600})
    before = int(time.time())
    result = session.bootstrap_first_party_session("Bearer verified-github")
    assert result["session_type"] == "owner_v2"
    assert before + 3600 <= result["expires_at"] <= int(time.time()) + 3600
