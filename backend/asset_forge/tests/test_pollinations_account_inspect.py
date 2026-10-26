"""Offline Pollinations account inspection tests; no network or credentials."""
import io
import json
from unittest.mock import patch
from backend.pollinations_account_inspect import inspect_account, _safe

class Response:
    status = 200
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        return json.dumps(self.data).encode()

def test_redacts_secrets_and_collects_subject():
    def fake(req, timeout):
        if req.full_url.endswith("/userinfo"):
            return Response({"sub": "subject-1", "access_token": "sk_hidden"})
        return Response({"balance": 12, "token": "sk_hidden"})
    with patch("backend.pollinations_account_inspect.urllib.request.urlopen", side_effect=fake) as call:
        result = inspect_account("sk_fake")
    assert call.call_count == 4
    assert result["provider_subject"] == "subject-1"
    assert result["owner_binding"] == "UNVERIFIED"
    assert result["spending_authorized"] is False
    assert "sk_hidden" not in str(result)

def test_invalid_credential_never_calls_network():
    with patch("backend.pollinations_account_inspect.urllib.request.urlopen") as call:
        result = inspect_account("invalid")
    call.assert_not_called()
    assert result["state"] == "UNKNOWN"

def test_nested_secrets_are_excluded():
    assert _safe({"budget": {"remaining": 3, "secret": "sk_fake"}, "token": "sk_fake"}) == {"budget": {"remaining": 3}}
