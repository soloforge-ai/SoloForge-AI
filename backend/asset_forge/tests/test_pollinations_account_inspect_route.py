"""Offline authorization tests for existing Pollinations sessions."""
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from backend.pollinations_oauth_router import pollinations_account_inspect, _OAuthSession

def test_existing_unbound_session_can_inspect():
    session = _OAuthSession(access_token="sk_mock", expires_at=9999999999, scope="")
    with patch("backend.soloforge_session.require_soloforge_session") as auth, \
         patch("backend.pollinations_oauth_router._get_session", return_value=session), \
         patch("backend.pollinations_account_inspect.inspect_account", return_value={"state": "EVIDENCE_COLLECTED"}) as inspect:
        result = pollinations_account_inspect(authorization="Bearer owner", pollinations_session="opaque-session")
    auth.assert_called_once()
    inspect.assert_called_once_with("sk_mock")
    assert result["state"] == "EVIDENCE_COLLECTED"

def test_unauthenticated_owner_never_loads_provider_session():
    with patch("backend.soloforge_session.require_soloforge_session", side_effect=HTTPException(401)), \
         patch("backend.pollinations_oauth_router._get_session") as load:
        with pytest.raises(HTTPException) as exc:
            pollinations_account_inspect(authorization=None, pollinations_session="opaque-session")
    assert exc.value.status_code == 401
    load.assert_not_called()

def test_missing_pollinations_session_fails_closed():
    with patch("backend.soloforge_session.require_soloforge_session"), \
         patch("backend.pollinations_oauth_router._get_session") as load:
        with pytest.raises(HTTPException) as exc:
            pollinations_account_inspect(authorization="Bearer owner", pollinations_session=None)
    assert exc.value.status_code == 401
    load.assert_not_called()

def test_unknown_pollinations_session_fails_closed():
    with patch("backend.soloforge_session.require_soloforge_session"), \
         patch("backend.pollinations_oauth_router._get_session", return_value=None):
        with pytest.raises(HTTPException) as exc:
            pollinations_account_inspect(authorization="Bearer owner", pollinations_session="unknown")
    assert exc.value.status_code == 404
