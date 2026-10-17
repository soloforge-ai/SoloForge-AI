"""Internal workload authentication boundary. Unwired; never trusts HTTP claims.

A trusted deployment component must supply the independent verifier. This
module does not turn owner, Supabase service_role, or provider tokens into
internal issuer authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

ISSUER = "soloforge-internal"
AUDIENCE = "trusted-qa-issuer"
SERVICE = "soloforge-asset-forge"

@dataclass(frozen=True)
class InternalPrincipal:
    service: str
    issuer: str
    audience: str
    expires_at: int

class WorkloadVerifier(Protocol):
    def verify(self, credential: str, *, issuer: str, audience: str) -> InternalPrincipal | None: ...

def authenticate_internal(*, credential: object, verifier: WorkloadVerifier | None,
                          now: int) -> InternalPrincipal | None:
    """Fail closed without an independently configured cryptographic verifier."""
    if (verifier is None or not isinstance(credential, str)
            or not credential or type(now) is not int):
        return None
    try:
        principal = verifier.verify(credential, issuer=ISSUER, audience=AUDIENCE)
    except Exception:
        return None
    if (type(principal) is not InternalPrincipal or principal.service != SERVICE
            or principal.issuer != ISSUER or principal.audience != AUDIENCE
            or type(principal.expires_at) is not int
            or principal.expires_at <= now or principal.expires_at > now + 300):
        return None
    return principal
