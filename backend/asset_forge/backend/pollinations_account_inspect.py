"""Read-only Pollinations account evidence; never return credentials or authorize spending."""
from __future__ import annotations
import json
import urllib.error
import urllib.request

BASE = "https://enter.pollinations.ai"
PATHS = {
    "identity": "https://enter.pollinations.ai/api/oauth/userinfo",
    "balance": "https://gen.pollinations.ai/account/balance",
}
SAFE = frozenset({"sub", "id", "keyId", "key_id", "type", "keyType", "key_type",
                  "status", "expiresAt", "expires_at", "scope", "scopes", "budget",
                  "remaining", "balance", "currency", "usage", "limit", "used",
                  "total", "period", "resetAt", "reset_at"})

def _safe(value, depth=0):
    if depth > 4:
        return None
    if isinstance(value, dict):
        return {k: _safe(v, depth + 1) for k, v in value.items() if k in SAFE}
    if isinstance(value, list):
        return [_safe(v, depth + 1) for v in value[:50]]
    if isinstance(value, str):
        return "[REDACTED]" if "sk_" in value or "Bearer " in value else value[:512]
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return None

def inspect_account(token: str) -> dict:
    if not isinstance(token, str) or not token.startswith("sk_"):
        return {"state": "UNKNOWN", "reason": "credential_invalid", "evidence": {}}
    evidence = {}
    from backend.pollinations_sk_lifecycle import provider_get
    for name, path in PATHS.items():
        status, data = provider_get(path, token)
        if status == 200:
            evidence[name] = {"http_status": status, "data": _safe(data)}
        else:
            reason = ("unauthorized" if status == 401 else "forbidden" if status == 403
                else "endpoint_unavailable" if status == 404 else "rate_limited" if status == 429
                else "provider_error" if status >= 500 else "network_error" if status == 0 else "http_error")
            evidence[name] = {"http_status": status or None, "reason": reason, "data": None}
    identity = evidence.get("identity", {}).get("data")
    subject = identity.get("sub") if isinstance(identity, dict) else None
    if not isinstance(subject, str) or not subject.strip() or subject == "[REDACTED]":
        subject = None
    return {"state": "EVIDENCE_COLLECTED" if isinstance(subject, str) and subject else "UNKNOWN",
            "provider_subject": subject if isinstance(subject, str) and subject else None,
            "owner_binding": "UNVERIFIED", "spending_authorized": False, "evidence": evidence}
