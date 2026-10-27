"""HTTP E2E for CI. NOT RUN in the local Unix-socket-restricted sandbox.

No tests are skipped here. Execute with the existing offline/seccomp runner in a
CI runtime that permits AF_UNIX wakeups. All provider/Auth/storage I/O is mocked.
"""
import hashlib
from io import BytesIO
import time
from uuid import uuid4
import wave
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_byop_repository import persistent, byop_db, binding_db, PRINCIPALS, REQUEST, auth
from backend.byop_router import router, get_flow


@pytest.fixture
def http_client(persistent):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_flow] = lambda: persistent['flow']
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize('principal', PRINCIPALS[1:])
def test_byop_http_real_policy_denies_member_generation(persistent, http_client, principal):
    from backend.byop_principal import require_generation_role
    persistent['flow'].generation_policy = require_generation_role
    headers = {'Authorization': auth(principal)}
    session = http_client.get('/v1/byop/session', headers=headers)
    assert session.status_code == 200
    assert session.json()['readiness']['pilot_role_eligible'] is False
    job = http_client.post('/v1/byop/jobs', headers=headers,
                           json={'asset_forge_request': REQUEST}).json()
    consent = http_client.post(f"/v1/byop/jobs/{job['id']}/consents", headers=headers,
        json={'credential_id': str(uuid4()), 'maximum_micro_pollen': 80,
              'expires_at': time.time() + 60})
    assert consent.status_code == 403
    execute = http_client.post('/v1/byop/executions', headers=headers,
        json={'consent_id': str(uuid4()), 'execution_id': str(uuid4())})
    assert execute.status_code == 403 and not persistent['calls']


@pytest.mark.parametrize('principal', PRINCIPALS)
def test_byop_http_owner_and_members_vertical_slice(persistent, http_client, principal, monkeypatch):
    # Historical member vertical slices use the explicit future-member fixture
    # policy. The test above checks today's real production denial policy.
    client = http_client
    headers = {'Authorization': auth(principal)}
    session = client.get('/v1/byop/session', headers=headers)
    assert session.status_code == 200 and session.json()['principal'] == principal
    token = 'sk_' + str(uuid4())
    persistent['subjects'][token] = persistent['flow'].repository.expected_subject(principal)
    response = client.post('/v1/byop/credentials', headers=headers, json={'access_token': token})
    assert response.status_code == 200 and token not in response.text
    assert response.headers['cache-control'] == 'no-store'
    cid = response.json()['credential_id']
    assert client.get('/v1/byop/credentials',headers=headers).json()['credentials'][0]['credential_id']==cid
    job = client.post('/v1/byop/jobs', headers=headers, json={
        'asset_forge_request': REQUEST, 'script': 'Offline authenticated CEO journey.'}).json()
    jid = job['id']
    consent_body = {'credential_id': cid, 'maximum_micro_pollen': 80, 'expires_at': time.time() + 240}
    assert client.post(f'/v1/byop/jobs/{jid}/consents', headers=headers, json=consent_body).status_code == 403
    verified = client.post(f'/v1/byop/credentials/{cid}/verify', headers=headers)
    assert verified.status_code == 200 and verified.json()['spending_authorized'] is False
    consent = client.post(f'/v1/byop/jobs/{jid}/consents', headers=headers, json=consent_body)
    assert consent.status_code == 200
    execute_body = {'consent_id': consent.json()['consent_id'], 'execution_id': str(uuid4())}
    response = client.post('/v1/byop/executions', headers=headers, json=execute_body)
    assert response.status_code == 200
    assert client.post('/v1/byop/executions', headers=headers, json=execute_body).status_code in (409, 503)
    assert len(persistent['calls']) == 1
    image = client.get(f'/v1/byop/jobs/{jid}/asset', headers=headers)
    assert image.status_code == 200 and image.headers['content-type'] == 'image/png'
    sha = hashlib.sha256(image.content).hexdigest()
    review = {'asset_sha256': sha, 'decision': 'REJECTED'}
    assert client.post(f'/v1/byop/jobs/{jid}/asset-review', headers=headers, json=review).status_code == 200
    assert client.post(f'/v1/byop/jobs/{jid}/render', headers=headers).status_code == 409
    review['decision'] = 'APPROVED'
    assert client.post(f'/v1/byop/jobs/{jid}/asset-review', headers=headers, json=review).status_code == 200
    out = BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000); wav.writeframes(b'\0\0' * 16000)
    assert client.post(f'/v1/byop/jobs/{jid}/audio', headers={**headers, 'Content-Type': 'audio/wav'}, content=out.getvalue()).status_code == 200
    rendered = client.post(f'/v1/byop/jobs/{jid}/render', headers=headers)
    assert rendered.status_code == 200
    assert rendered.json()['render_qa']['source_asset_sha256'] == sha
    monkeypatch.setattr('backend.publora_publishing._signed_storage_url', lambda *a: 'https://offline.invalid/video')
    assert client.get(f'/v1/byop/jobs/{jid}/video', headers=headers).json()['url'] == 'https://offline.invalid/video'
    disconnected = client.post(f'/v1/byop/credentials/{cid}/disconnect', headers=headers)
    assert disconnected.status_code == 200 and not disconnected.json()['upstream_revocation_confirmed']
    assert client.get(f'/v1/byop/credentials/{cid}', headers=headers).json()['connected'] is False
    assert len(persistent['calls']) == 1


def test_byop_http_cross_principal_body_and_secret_isolation(persistent, http_client):
    client = http_client
    p1, p2 = PRINCIPALS[1:]
    headers = {'Authorization': auth(p1)}
    foreign = {'Authorization': auth(p2)}
    token = 'sk_' + str(uuid4())
    cid = client.post('/v1/byop/credentials', headers=headers, json={'access_token': token}).json()['credential_id']
    jid = client.post('/v1/byop/jobs', headers=headers, json={'asset_forge_request': REQUEST}).json()['id']
    assert client.get('/v1/byop/credentials',headers=foreign).json()['credentials']==[]
    for path in [f'/credentials/{cid}', f'/jobs/{jid}', f'/jobs/{jid}/asset']:
        assert client.get('/v1/byop' + path, headers=foreign).status_code in (403, 404, 409, 503)
    for action in ['verify', 'disconnect']:
        assert client.post(f'/v1/byop/credentials/{cid}/{action}', headers=foreign).status_code in (403, 404, 503)
    response = client.post('/v1/byop/credentials', headers=headers,
                           json={'access_token': token, 'principal': p2, 'verification_status': 'VERIFIED'})
    assert response.status_code == 422 and token not in response.text
    assert client.get('/v1/byop/session').status_code == 401
    persistent['db'].query("update public.soloforge_memberships set status='SUSPENDED' where user_id=$1", [p1.split(':')[1]])
    assert client.get('/v1/byop/session', headers=headers).status_code == 403
    assert not persistent['calls']
