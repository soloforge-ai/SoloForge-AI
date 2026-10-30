"""Owner denial must never mutate the independently persisted provider session."""
import pytest
from fastapi import HTTPException
from backend.asset_forge.backend import pollinations_oauth_router as routes


@pytest.mark.parametrize('code', [401, 403])
def test_owner_denial_precedes_provider_lookup(monkeypatch, code):
    def denied(_):
        raise HTTPException(code, 'Owner authorization required')
    monkeypatch.setattr(routes, '_owner', denied)
    monkeypatch.setattr(routes, '_get_session', lambda _: pytest.fail('Unauthorized provider lookup'))
    with pytest.raises(HTTPException) as error:
        routes.pollinations_status(None, 'expired-owner', 'opaque-provider-handle')
    assert error.value.status_code == code


def test_wrong_owner_does_not_remove_provider_session(monkeypatch):
    from types import SimpleNamespace
    session = SimpleNamespace(submitted_by_owner='owner-a', verification_status='PENDING_VERIFICATION', expires_at=9999999999, scope='profile')
    monkeypatch.setattr(routes, '_get_session', lambda _: session)
    monkeypatch.setattr(routes, '_owner', lambda _: 'owner-b')
    with pytest.raises(HTTPException) as error:
        routes.pollinations_status(None, 'other-owner', 'opaque-handle')
    assert error.value.status_code == 404
    monkeypatch.setattr(routes, '_owner', lambda _: 'owner-a')
    result = routes.pollinations_status(None, 'renewed-owner', 'opaque-handle')
    assert result['connected'] is True
    assert result['spending_authorized'] is False


def test_missing_provider_session_is_not_connected(monkeypatch):
    monkeypatch.setattr(routes, '_owner', lambda _: 'owner-a')
    monkeypatch.setattr(routes, '_get_session', lambda _: None)
    assert routes.pollinations_status(None, 'valid-owner', 'expired-or-revoked') == {'connected': False}
