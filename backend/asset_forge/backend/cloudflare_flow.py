"""Owner-only application wiring over the existing BYOP job/review flow.

Live mode requires explicit server capability and HTTP transport; defaults OFF.
No provider ownership verification or budget provisioning is exposed to clients.
"""
import hashlib
from fastapi import HTTPException
from .byop_flow import Flow
from .byop_principal import authenticate
from .cloudflare_image import MODEL
from .byop_runtime import cloudflare_mock_dispatch


class CloudflareFlow(Flow):
    provider = 'cloudflare'

    def __init__(self, repository, ledger, fake_transport=None, *, transport=None, enabled=False):
        if transport is not None and (fake_transport is not None or not enabled or not transport.enabled):
            raise ValueError('Explicit enabled live transport required')
        fake_transport = transport if transport is not None else fake_transport
        self.mode = 'cloudflare_http' if transport is not None else 'offline_mock'
        if ledger.provider != 'cloudflare' or ledger.unit != 'neurons' or fake_transport is None:
            raise ValueError('Explicit Cloudflare capability required')
        super().__init__(self.owner, repository, ledger, None, None)
        self.fake_transport = fake_transport

    @staticmethod
    def owner(authorization):
        principal = authenticate(authorization)
        if principal.kind != 'owner':
            raise HTTPException(403, 'Owner V2 required for Cloudflare capability')
        return principal

    def connect(self, authorization, token, account_id=None):
        principal = self.authenticate(authorization)
        return self.repository.submit_cloudflare(principal.key, account_id, token)

    def credential(self, principal, credential_id):
        record = self.repository.cloudflare_credential(principal.key, credential_id)
        if (not record or record.get('revoked') or record.get('verification_status') != 'VERIFIED'
                or not record.get('provider_ownership_verified') or record['expires_at'] <= self.ledger.clock()):
            raise HTTPException(403, 'Verified Owner Cloudflare credential required')
        return record

    def create_job(self, authorization, request, script=''):
        principal = self.authenticate(authorization)
        if (set(request) != {'prompt','model'} or request.get('model') != MODEL
                or not isinstance(request.get('prompt'), str) or not 1 <= len(request['prompt'].strip()) <= 2048):
            raise HTTPException(400, 'Bounded prompt and eligible Cloudflare model required')
        return self.repository.create_cloudflare_job(principal.key, request['prompt'].strip(), MODEL, mode=self.mode)

    def job(self, principal, job_id):
        job = super().job(principal, job_id)
        if (job['content_package'].get('byop_provider') != 'cloudflare'
                or job['content_package'].get('generation_mode','offline_mock') != self.mode):
            raise HTTPException(404, 'Cloudflare job unavailable')
        return job

    def snapshot(self, principal, credential_id, job_id):
        credential = self.credential(principal, credential_id)
        job = self.job(principal, job_id)
        prompt = job['content_package']['asset_forge_request']['prompt']
        snapshot = {'provider':'cloudflare','budget_unit':'neurons','credential_id':credential_id,
            'account_id':credential['account_id'], 'credential_sha256':hashlib.sha256(credential['token'].encode()).hexdigest(),
            'job_id':job_id,'revision':job['revision'],'operation':'text_image','model':job['model'],'image_count':1,
            'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
            'reference_sha256':hashlib.sha256(b'').hexdigest(),'settings':{'steps':4,'job_bound':True}}
        if self.mode == 'cloudflare_http':
            snapshot['settings']['transport_mode'] = self.mode
        return snapshot

    def execute(self, authorization, consent_id, execution_id):
        principal = self.authenticate(authorization)
        execution = self.ledger.reserve(principal.key, consent_id, execution_id)
        snap = execution['snapshot']
        current = self.snapshot(principal, snap['credential_id'], snap['job_id'])
        if current != snap:
            raise HTTPException(409, 'Immutable request changed')
        job = self.job(principal, snap['job_id'])
        credential = self.credential(principal, snap['credential_id'])
        if self.authenticate(authorization) != principal:
            raise HTTPException(403, 'Owner identity changed before claim')
        def store(data, metadata):
            from .branding import stamp_image_bytes
            image, branding = stamp_image_bytes(data)
            sha = hashlib.sha256(image).hexdigest()
            branding['asset_forge_manifest'] = {'provider':'cloudflare','generation_mode':self.mode,
                'generation_layout':'text_image','ceo_identity_verified':False,'model':snap['model']}
            return self.repository.store_content_asset(principal.key, snap['job_id'], snap['revision'], image, sha, branding)
        _, asset = cloudflare_mock_dispatch(self.ledger, principal.key, execution, credential,
            job['content_package']['asset_forge_request']['prompt'], fake_transport=self.fake_transport,
            repository=self.repository, store_asset=store)
        return asset

    def disconnect(self, authorization, credential_id):
        return self.repository.disconnect_cloudflare(self.authenticate(authorization).key, credential_id)

    def render_job(self, *args):
        raise HTTPException(503, 'Cloudflare mock image has no CEO render capability')

    def export_asset(self, authorization, job_id, format):
        principal = self.authenticate(authorization)
        job = self.job(principal, job_id)
        package = job['content_package']
        data = self.repository.asset_bytes(principal.key, job_id)
        sha = hashlib.sha256(data).hexdigest()
        if (job['status'] != 'ASSET_READY' or package.get('asset_review_status') != 'APPROVED'
                or package.get('asset_review_sha256') != sha or package.get('asset_sha256') != sha):
            raise HTTPException(409, 'Exact image approval required for export')
        if format == 'png':
            return data
        if format != 'zip':
            raise HTTPException(400, 'PNG or ZIP export required')
        from runtime import asset_forge_main as forge
        manifest = {**package['asset_forge_manifest'], 'job_id':job_id,
            'approval_sha256':sha, 'files':[{'name':'image.png','sha256':sha}]}
        return forge._zip_image_files([('image.png',data)], 'cloudflare_'+job_id, data, manifest,
                                     include_raw_provider=False)
