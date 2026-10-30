"""Single-attempt server transport; no redirects, proxies, retries or key fallback.

Contract: developers.cloudflare.com/workers-ai/models/flux-1-schnell/
POST /client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell
JSON {prompt,steps}; API envelope {success:true,errors:[],result:{image:base64}}.
Only text-to-image is supported. A response is not a settled charge receipt.
"""
import json
import re
import time
import urllib.request
from fastapi import HTTPException
from .cloudflare_image import MODEL

MAX_RESPONSE = 16_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Provider redirect denied')


class CloudflareHTTPTransport:
    mode = 'cloudflare_http'

    def __init__(self, *, enabled=False, opener=None):
        self.enabled = enabled is True
        self._opener = opener

    def __call__(self, *, account_id, token, model, body):
        if not self.enabled:
            raise HTTPException(503, 'Cloudflare live transport disabled')
        if (not isinstance(account_id, str) or not re.fullmatch(r'[0-9a-f]{32}', account_id)
                or model != MODEL or not isinstance(token, str) or not 1 <= len(token) <= 4096
                or not token.isascii() or any(ord(c) <= 32 or ord(c) >= 127 for c in token)
                or not isinstance(body, dict) or set(body) != {'prompt', 'steps'}
                or type(body['steps']) is not int or body['steps'] != 4
                or not isinstance(body['prompt'], str) or not 1 <= len(body['prompt']) <= 2048):
            raise ValueError('Cloudflare request contract denied')
        request = urllib.request.Request(
            'https://api.cloudflare.com/client/v4/accounts/'+account_id+'/ai/run/'+MODEL,
            data=json.dumps(body, separators=(',', ':')).encode(), method='POST',
            headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json',
                     'Accept':'application/json', 'Accept-Encoding':'identity'})
        try:
            # Construct lazily, AFTER the retained durable CALL_STARTED boundary.
            # urllib does not retry POST. Disable environment proxies and redirects.
            opener = self._opener or urllib.request.build_opener(
                urllib.request.ProxyHandler({}), NoRedirect()).open
            deadline = time.monotonic()+60
            with opener(request, timeout=60) as response:
                if response.status != 200:
                    raise ValueError()
                if response.headers.get_content_type() != 'application/json':
                    raise ValueError()
                raw = bytearray()
                while len(raw) <= MAX_RESPONSE:
                    if time.monotonic() >= deadline:
                        raise TimeoutError()
                    chunk = response.read1(min(65536, MAX_RESPONSE+1-len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
                if not raw or len(raw) > MAX_RESPONSE:
                    raise ValueError()
            result = json.loads(raw)
            if (not isinstance(result, dict) or result.get('success') is not True
                    or result.get('errors') != [] or not isinstance(result.get('result'), dict)
                    or not isinstance(result['result'].get('image'), str)):
                raise ValueError()
            return {'status':200, 'result':{'image':result['result']['image']}}
        except Exception:
            # Never expose exception text, request headers or upstream error bodies.
            # Dispatch owns UNKNOWN + retained reservation; never infer no charge.
            raise ValueError('Cloudflare HTTP outcome unconfirmed') from None
