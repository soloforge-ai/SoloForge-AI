"""Actual HTTP transport interface, fake opener + retained SQL/HTTP/storage flow.

No Cloudflare request, quota use, production storage or production database.
"""
import base64
from email.message import Message
import hashlib
from io import BytesIO
import json
from uuid import uuid4
import zipfile
import pytest
from PIL import Image
from fastapi import HTTPException
from test_cloudflare_application import (
    app, application_db, persistent, byop_db, binding_db, prepare, authorize, PRINCIPAL, TOKEN,
)
from backend.cloudflare_http import CloudflareHTTPTransport, MAX_RESPONSE, NoRedirect
from backend.cloudflare_flow import CloudflareFlow
from backend.cloudflare_image import MODEL
from backend import byop_router


class Reply(BytesIO):
    def __init__(self, raw, status=200, mime='application/json'):
        super().__init__(raw)
        self.status = status
        self.headers = Message()
        self.headers['Content-Type'] = mime


def envelope(format='JPEG'):
    image = BytesIO()
    Image.new('RGB', (16, 16), 'blue').save(image, format)
    return json.dumps({'success':True, 'errors':[],
        'result':{'image':base64.b64encode(image.getvalue()).decode()}}).encode()


def configure(app, *, raw=None, status=200, mime='application/json', failure=None):
    calls = []
    def opener(request, **kwargs):
        # The actual urllib Request and fixed URL/body are exercised, not a
        # replacement provider adapter. This callable never opens any socket.
        calls.append(request)
        assert kwargs == {'timeout':60}
        assert request.full_url == 'https://api.cloudflare.com/client/v4/accounts/'+'a'*32+'/ai/run/'+MODEL
        assert request.get_method() == 'POST'
        assert request.get_header('Authorization') == 'Bearer '+TOKEN
        assert json.loads(request.data) == {'prompt':'A cat on a quiet street','steps':4}
        if failure: raise failure(TOKEN)
        return Reply(envelope() if raw is None else raw, status, mime)
    transport = CloudflareHTTPTransport(enabled=True, opener=opener)
    flow = CloudflareFlow(app['repo'], app['ledger'], transport=transport, enabled=True)
    app['api'].dependency_overrides[byop_router.get_cloudflare_capability] = lambda:flow
    app['flow'] = flow
    return calls


def execute(app):
    cid, jid = prepare(app)
    consent = authorize(app, cid, jid).json()
    eid = str(uuid4())
    body = {'consent_id':consent['consent_id'], 'execution_id':eid}
    return cid, jid, eid, body


@pytest.mark.parametrize('format', ['PNG','JPEG'])
def test_owner_http_transport_to_private_review_and_retained_export(app, format):
    calls = configure(app, raw=envelope(format))
    h = app['http']; cid, jid, eid, body = execute(app)
    assert h('GET', f'/jobs/{jid}/export').status_code == 409
    result = h('POST', '/executions', json=body)
    assert result.status_code == 200, result.text
    assert len(calls) == 1
    snapshot = app['ledger'].store.read(PRINCIPAL)[1]['executions'][eid]['snapshot']
    assert snapshot['settings']['transport_mode'] == 'cloudflare_http'
    assert snapshot['credential_id'] == cid and snapshot['model'] == MODEL
    job = h('GET', f'/jobs/{jid}').json()
    assert job['content_package']['asset_mode'] == 'cloudflare_http'
    assert job['content_package']['ceo_identity_required'] is False
    image = h('GET', f'/jobs/{jid}/asset').content
    assert image.startswith(b'\x89PNG')
    sha = hashlib.sha256(image).hexdigest()
    assert h('GET', f'/jobs/{jid}/export').status_code == 409
    assert h('POST', f'/jobs/{jid}/asset-review', json={'decision':'APPROVED','asset_sha256':sha}).status_code == 200
    png = h('GET', f'/jobs/{jid}/export', params={'format':'png'})
    assert png.status_code == 200 and png.content == image and png.headers['cache-control'] == 'no-store'
    exported = h('GET', f'/jobs/{jid}/export', params={'format':'zip'})
    assert exported.status_code == 200
    with zipfile.ZipFile(BytesIO(exported.content)) as archive:
        prefix = 'cloudflare_'+jid+'/'
        assert archive.read(prefix+'image.png') == image
        assert not any('/raw/' in name for name in archive.namelist())
        manifest = json.loads(archive.read(prefix+'manifest.json'))
        assert manifest['approval_sha256'] == sha and manifest['ceo_identity_verified'] is False
    assert TOKEN.encode() not in exported.content
    assert h('POST', '/executions', json=body).status_code == 409 and len(calls) == 1
    assert h('GET', f'/jobs/{jid}/export', headers={}).status_code in (401,403)
    assert h('POST', f'/credentials/{cid}/disconnect').status_code == 200


@pytest.mark.parametrize('case', ['timeout','unauthorized','quota','server','malformed','false_success','bad_image','wrong_mime','oversize','storage'])
def test_http_failure_unknown_held_no_replay_no_secret(app, monkeypatch, case):
    raw, status, mime, failure = envelope(), 200, 'application/json', None
    if case == 'timeout': failure = TimeoutError
    if case in ('unauthorized','quota','server'): status = {'unauthorized':401,'quota':429,'server':500}[case]
    if case == 'malformed': raw = b'not json '+TOKEN.encode()
    if case == 'false_success': raw = b'{"success":false,"errors":[],"result":{"image":"AAAA"}}'
    if case == 'bad_image': raw = b'{"success":true,"errors":[],"result":{"image":"AAAA"}}'
    if case == 'wrong_mime': mime = 'text/html'
    if case == 'oversize': raw = b'x'*(MAX_RESPONSE+1)
    calls = configure(app, raw=raw, status=status, mime=mime, failure=failure)
    if case == 'storage':
        from backend import content_asset_generation
        def fail(*args): raise RuntimeError(TOKEN)
        monkeypatch.setattr(content_asset_generation, '_upload_asset', fail)
    _, jid, eid, body = execute(app)
    for _ in range(2): assert app['http']('POST', '/executions', json=body).status_code == 409
    assert len(calls) == 1
    state = app['ledger'].store.read(PRINCIPAL)[1]['executions'][eid]
    assert state['state'] == 'UNKNOWN' and state['reserved'] == 70
    assert app['http']('GET', f'/jobs/{jid}/export').status_code == 409


def test_live_transport_default_flags_and_redirects_fail_closed(app, monkeypatch):
    from backend.byop_ledger import unavailable_pricing
    monkeypatch.delenv('SOLOFORGE_CLOUDFLARE_LIVE_ENABLED', raising=False)
    assert byop_router.get_cloudflare_capability(unavailable_pricing) is None
    monkeypatch.setenv('SOLOFORGE_CLOUDFLARE_LIVE_ENABLED', 'true')
    monkeypatch.delenv('CLOUDFLARE_BYOP_KEYRING_JSON', raising=False)
    assert byop_router.get_cloudflare_capability(unavailable_pricing) is None
    with pytest.raises(HTTPException):
        CloudflareHTTPTransport(opener=lambda *a, **k:pytest.fail('disabled transport'))(
            account_id='a'*32, token=TOKEN, model=MODEL, body={'prompt':'cat','steps':4})
    with pytest.raises(ValueError): NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.invalid')


def test_exact_credential_a_dispatch_and_revoked_denial(app):
    calls = configure(app)
    cid, jid, _, body = execute(app)
    other = app['repo'].submit_cloudflare(PRINCIPAL, 'a'*32, TOKEN+'-B')['credential_id']
    assert other != cid
    assert app['http']('POST', '/executions', json=body).status_code == 200
    assert len(calls) == 1 and calls[0].get_header('Authorization') == 'Bearer '+TOKEN


def test_revoked_credential_denies_http_dispatch(app):
    calls = configure(app)
    cid2, jid2 = prepare(app)
    consent = authorize(app, cid2, jid2).json()
    app['http']('POST', f'/credentials/{cid2}/disconnect')
    assert app['http']('POST', '/executions', json={'consent_id':consent['consent_id'], 'execution_id':str(uuid4())}).status_code in (403,409)
    assert not calls


@pytest.mark.parametrize('mutation', [
    {'account_id':'other-account'}, {'model':'@cf/unsupported'}, {'token':'bad\r\nheader'},
    {'body':{'prompt':'cat','steps':True}}, {'body':{'prompt':'cat','steps':4,'image':'unsupported'}},
])
def test_invalid_http_contract_never_opens_socket(mutation):
    args = {'account_id':'a'*32, 'model':MODEL, 'token':TOKEN, 'body':{'prompt':'cat','steps':4}}
    args.update(mutation)
    with pytest.raises(ValueError):
        CloudflareHTTPTransport(enabled=True, opener=lambda *a, **k:pytest.fail('invalid dispatch'))(**args)


def test_http_flow_requires_consent_budget_and_owner(app):
    calls = configure(app)
    cid, jid = prepare(app, verified=False)
    assert authorize(app, cid, jid).status_code == 403
    assert app['http']('POST','/executions',json={'consent_id':str(uuid4()),'execution_id':str(uuid4())}).status_code == 409
    assert app['http']('POST','/jobs',headers={},json={'asset_forge_request':{'prompt':'cat','model':MODEL}}).status_code in (401,403)
    app['db'].query("update public.pollinations_sessions set verification_status='VERIFIED',provider_ownership_verified=true,provider_subject=provider_account_id,byop_verified_at=now(),independent_verification_evidence='OFFLINE fixture' where id=$1",[cid])
    consent = authorize(app, cid, jid).json()
    app['db'].query("update public.byop_ledgers set state=jsonb_set(state,'{budget}','1') where principal=$1",[PRINCIPAL])
    assert app['http']('POST','/executions',json={'consent_id':consent['consent_id'],'execution_id':str(uuid4())}).status_code == 409
    assert not calls


def test_live_mode_request_is_immutable_and_unverified_prices_deny(app):
    from backend.byop_ledger import unavailable_pricing
    calls = configure(app)
    cid, jid = prepare(app)
    with pytest.raises(RuntimeError):
        app['db'].query("update public.content_jobs set content_package=jsonb_set(content_package,'{generation_mode}','\"offline_mock\"') where id=$1",[jid], 'service_role')
    app['ledger'].pricing = unavailable_pricing
    assert authorize(app, cid, jid).status_code == 503
    assert not calls
