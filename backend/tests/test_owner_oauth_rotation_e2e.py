"""Fake-provider owner login -> OAuth callback -> handoff -> rotation contract."""
from urllib.parse import urlparse, parse_qs
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend import pollinations_oauth_router as r
from backend import soloforge_session as owner
from backend.owner_provider_binding import (VerifiedIdentity, CredentialMetadata,
    establish_binding, rotate_credential, BindingRejected)

class Store:
    def __init__(self):
        self.identity = None
        self.rotations = []
    def load(self, user):
        return self.identity if self.identity and self.identity.owner_user_id == user else None
    def insert_once(self, identity):
        if self.identity: raise BindingRejected('immutable')
        self.identity = identity
    def record_rotation(self, user, key):
        self.rotations.append((user, key))

@pytest.fixture
def flow(monkeypatch, tmp_path):
    monkeypatch.setenv('SOLOFORGE_SESSION_SECRET', 'x'*40)
    monkeypatch.setenv('SOLOFORGE_OFFLINE_FAKE_PROVIDER', '1')
    monkeypatch.setenv('SOLOFORGE_OFFLINE_BINDING_SQLITE', str(tmp_path / 'binding.sqlite'))
    monkeypatch.setenv('POLLINATIONS_CLIENT_ID', 'pk_fake')
    monkeypatch.setenv('POLLINATIONS_REDIRECT_URI', 'https://testserver/auth/pollinations/callback')
    monkeypatch.setenv('POLLINATIONS_TRUSTED_APP_KEY_ID', 'internal-app')
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.setattr(r, 'exchange_authorization_code', lambda *a, **kw: {
        'access_token':'synthetic', 'expires_in': 600, 'scope':'profile usage'})
    monkeypatch.setattr(r, '_verified_grant', lambda token: {
        'provider_subject':'subject-1', 'key_owner':'provider-account',
        'key_id':'key-1', 'internal_app_key_id':'internal-app', 'key_expires_at': 2000000000})
    with r._lock:
        r._transactions.clear(); r._sessions.clear(); r._handoffs.clear(); r._login_tickets.clear()
    app=FastAPI(); app.include_router(r.router)
    client=TestClient(app,base_url='https://testserver')
    bearer='Bearer '+owner.issue_session(owner._owner_user_id()).session_id
    yield client,bearer
    with r._lock:
        r._transactions.clear(); r._sessions.clear(); r._handoffs.clear(); r._login_tickets.clear()

def login(client, bearer):
    ticket=client.post('/auth/pollinations/login-ticket',headers={'Authorization':bearer}).json()['login_ticket']
    login=client.get('/auth/pollinations/login',params={'client':'mobile','login_ticket':ticket},follow_redirects=False)
    assert login.status_code == 302
    state=parse_qs(urlparse(login.headers['location']).query)['state'][0]
    callback=client.get('/auth/pollinations/callback',params={'code':'fake-code','state':state},follow_redirects=False)
    assert callback.status_code == 302
    code=parse_qs(urlparse(callback.headers['location']).query)['code'][0]
    return code

def test_owner_oauth_handoff_and_key_rotation(flow):
    client,bearer=flow
    assert client.get('/auth/pollinations/login').status_code == 401
    assert client.post('/auth/pollinations/login-ticket').status_code == 401
    code=login(client,bearer)
    assert client.post('/auth/pollinations/mobile/exchange',json={'code':code}).status_code == 401
    result=client.post('/auth/pollinations/mobile/exchange',json={'code':code},headers={'X-SoloForge-Authorization':bearer})
    assert result.status_code == 200
    sid=result.json()['session_token']
    assert 'synthetic' not in result.text
    headers={'Authorization':'Bearer '+sid,'X-SoloForge-Authorization':bearer}
    assert client.get('/auth/pollinations/status',headers=headers).json()['connected']
    assert r.get_pollinations_access_token_from_authorization('Bearer '+sid,bearer) == 'synthetic'
    with pytest.raises(Exception):
        r.get_pollinations_access_token_from_authorization('Bearer '+sid,None)
    store=Store(); identity=VerifiedIdentity(owner._owner_user_id(),'provider-account','internal-app')
    establish_binding(store,identity,authenticated_owner_id=owner._owner_user_id())
    for keyid in ('key-1','key-2'):
        rotate_credential(store,authenticated_owner_id=owner._owner_user_id(),verified_key=CredentialMetadata(keyid,'provider-account','internal-app',True,200),now=100)
    assert store.identity == identity
    assert len(store.rotations) == 2
    with pytest.raises(BindingRejected):
        rotate_credential(store,authenticated_owner_id=owner._owner_user_id(),verified_key=CredentialMetadata('key-3','other-account','internal-app',True,200),now=100)
    assert len(store.rotations)==2

def test_invalid_grant_denies_callback_without_session(flow,monkeypatch):
    client,bearer=flow
    monkeypatch.setattr(r,'_verified_grant',lambda token: {})
    ticket=client.post('/auth/pollinations/login-ticket',headers={'Authorization':bearer}).json()['login_ticket']
    response=client.get('/auth/pollinations/login',params={'login_ticket':ticket},follow_redirects=False)
    state=parse_qs(urlparse(response.headers['location']).query)['state'][0]
    callback=client.get('/auth/pollinations/callback',params={'code':'fake','state':state},follow_redirects=False)
    assert callback.status_code==403
    assert not r._sessions
