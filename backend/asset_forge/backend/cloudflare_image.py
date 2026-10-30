"""Mock-only Workers AI adapter. No network implementation or runtime enable flag."""
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
from PIL import Image
from fastapi import HTTPException

MODEL = '@cf/black-forest-labs/flux-1-schnell'


class CloudflareImage:
    def __init__(self, *, fake_transport=None):
        self.transport = fake_transport

    def dispatch(self, ledger, principal, execution, credential, prompt, *, repository=None, store_asset=None):
        if self.transport is None:
            raise HTTPException(503, 'Cloudflare generation is disabled')
        if ledger.provider != 'cloudflare' or ledger.unit != 'neurons':
            raise HTTPException(409, 'Cloudflare Neurons ledger required')
        if repository is not None:
            # Reload immediately before validation/claim. The SQL claim then
            # locks the authoritative credential and principal with the ledger.
            credential = repository.cloudflare_credential(principal, execution['snapshot']['credential_id'])
        from .byop_ledger import SupabaseLedger
        if isinstance(ledger.store, SupabaseLedger) and repository is None:
            raise HTTPException(503, 'Authoritative credential repository required')
        source_credential = credential
        credential = deepcopy(credential)
        snap = deepcopy(execution['snapshot'])
        if (not principal.startswith('owner:') or not credential
                or credential.get('principal') != principal
                or credential.get('provider') != 'cloudflare'
                or credential.get('id') != snap.get('credential_id')
                or not credential.get('token') or not credential.get('account_id')
                or credential.get('account_id') != snap.get('account_id')
                or credential.get('verification_status') != 'VERIFIED'
                or credential.get('provider_ownership_verified') is not True
                or credential.get('revoked') or credential.get('disconnected')
                or credential.get('expires_at', 0) <= ledger.clock()
                or hashlib.sha256(credential['token'].encode()).hexdigest() != snap.get('credential_sha256')
                or snap.get('provider') != 'cloudflare' or snap.get('budget_unit') != 'neurons'
                or snap.get('model') != MODEL or snap.get('operation') != 'text_image'
                or snap.get('reference_sha256') != hashlib.sha256(b'').hexdigest()
                or hashlib.sha256(prompt.encode()).hexdigest() != snap.get('prompt_sha256')
                or not 1 <= len(prompt) <= 2048
                or snap.get('settings') not in ({'steps':4}, {'steps':4,'job_bound':True})):
            raise HTTPException(403, 'Exact Owner/provider/credential/request binding required')
        ledger.check_dispatch(principal, execution, snap, credential)
        # CAS is the one-use durable claim; failure cannot dispatch. Concurrent
        # losers never enter transport. Production Supabase construction is denied.
        ledger.start(principal, execution['id'], snap)
        try:
            # A callback/claim may mutate the supplied object. Never reread its
            # token for dispatch; detect visible revocation or identity changes.
            # This is not a substitute for future authoritative DB revalidation.
            if source_credential != credential:
                raise ValueError('Credential changed during claim')
            response = self.transport(
                account_id=credential['account_id'], token=credential['token'],
                model=MODEL, body={'prompt': prompt, 'steps': 4})
            if response.get('status') != 200:
                raise ValueError('Provider rejected or quota exhausted')
            encoded = response.get('result', {}).get('image')
            if not isinstance(encoded, str) or len(encoded) > 16_000_000:
                raise ValueError('Invalid image response')
            data = base64.b64decode(encoded, validate=True)
            with Image.open(BytesIO(data)) as image:
                if image.width * image.height > 16_000_000:
                    raise ValueError('Image too large')
                image.verify()
            asset = {'provider':'cloudflare','sha256':hashlib.sha256(data).hexdigest(),
                     'ceo_identity_verified':False}
            if store_asset is not None:
                asset = store_asset(data, asset)
        except Exception:
            ledger.outcome(principal, execution['id'])
            raise HTTPException(409, 'Cloudflare outcome unknown; reservation held; no replay') from None
        ledger.outcome(principal, execution['id'], generated=True, asset=asset)
        return data, asset
