"""Trusted same-credential read-only collection. No default live transport.

Transport is a server dependency, not request data. Enabling a real authenticated
transport requires separate authorization; offline fixtures provide deterministic
responses. Prices and balances remain evidence, never provider spending caps.
"""
from copy import deepcopy
import hashlib
import json
import time
import urllib.request
from fastapi import HTTPException
from .byop_pricing import CANONICAL_MODEL


def disabled_transport(path, token):
    raise HTTPException(503, "Authenticated provider evidence transport is not activated")


class ProviderEvidenceTransport:
    """Explicitly installed server adapter; never selected by default.

    Fixed GET-only contract, no redirect/retry, bounded response and timeout.
    Callers must separately authorize its installation and authenticated reads.
    """
    def __call__(self, path, token):
        if path not in {"/models", "/account/key", "/account/balance"}:
            raise HTTPException(503, "Unreviewed evidence endpoint")
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        request = urllib.request.Request("https://gen.pollinations.ai" + path,
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"}, method="GET")
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=10) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError()
            return json.loads(data)
        except Exception:
            raise HTTPException(503, "Read-only provider evidence unavailable") from None


class EvidenceCollector:
    def __init__(self, repository, transport=disabled_transport, clock=time.time):
        self.repository, self.transport, self.clock = repository, transport, clock

    def collect(self, principal, snapshot, credential):
        if not principal.startswith("owner:"):
            raise HTTPException(403, "Owner pilot evidence only")
        current = self.repository.credential(principal, snapshot["credential_id"])
        if (not current or current != credential or current.get("principal") != principal
                or current.get("verification_status") != "VERIFIED"
                or current.get("provider_ownership_verified") is not True
                or current.get("revoked") or current.get("disconnected")
                or current.get("expires_at", 0) <= self.clock()
                or current.get("provider_subject") != self.repository.expected_subject(principal)):
            raise HTTPException(403, "Independent owner and selected credential verification required")
        values, observed = {}, {}
        # Capture request START times, so a slow response cannot acquire a new TTL.
        for name, path in (("catalog", "/models"), ("key", "/account/key"),
                           ("balance", "/account/balance")):
            observed[name] = self.clock()
            try:
                values[name] = deepcopy(self.transport(path, current["token"]))
            except Exception:
                raise HTTPException(503, "Trusted provider evidence unavailable; no automatic retry") from None
        rows = values["catalog"]
        if not isinstance(rows, list):
            raise HTTPException(503, "Reviewed model catalog response unavailable")
        matches = [r for r in rows if isinstance(r, dict)
                   and r.get("name", r.get("id")) == CANONICAL_MODEL]
        if len(matches) != 1:
            raise HTTPException(503, "Exactly one reviewed catalog model required")
        return {**values, "catalog": matches[0], "observed_at": observed,
                "principal": principal, "credential_id": snapshot["credential_id"],
                "credential_digest": hashlib.sha256(current["token"].encode()).hexdigest()}
