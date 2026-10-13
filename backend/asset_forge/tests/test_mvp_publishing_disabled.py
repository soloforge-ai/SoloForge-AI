"""MVP regression tests: Publora cannot dispatch through API or direct adapter."""
from __future__ import annotations

from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from backend import publishing_policy
from backend import publishing_api
from backend import publora_publishing


def test_publishing_gate_is_not_unlocked_by_env(monkeypatch):
    monkeypatch.setenv("PUBLORA_API_KEY", "fake-test-only")
    monkeypatch.setenv("SOLOFORGE_RUN_EMBEDDED_WORKERS", "true")
    with pytest.raises(HTTPException) as error:
        publishing_policy.require_publishing_enabled()
    assert error.value.status_code == 503


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_direct_publora_adapter_fails_before_network(monkeypatch, method):
    network = Mock(side_effect=AssertionError("Publora must not be called"))
    monkeypatch.setattr(publora_publishing.urllib.request, "urlopen", network)
    monkeypatch.setenv("PUBLORA_API_KEY", "fake-test-only")
    with pytest.raises(HTTPException) as error:
        publora_publishing._publora_request(method, "/platform-connections")
    assert error.value.status_code == 503
    network.assert_not_called()


def test_publish_submission_fails_before_database(monkeypatch):
    database = Mock(side_effect=AssertionError("Publishing must not mutate jobs"))
    monkeypatch.setattr(publishing_api, "_supabase_request", database)
    with pytest.raises(HTTPException) as error:
        publishing_api._submit("job", [], publishing_api.publish_now_time())
    assert error.value.status_code == 503
    database.assert_not_called()
