"""Read-only Pollinations account evidence; never return credentials or authorize spending."""
from __future__ import annotations
import json
import urllib.error
import urllib.request

BASE = "https://enter.pollinations.ai"
PATHS = {"identity": "/api/oauth/userinfo", "key": "/api/account/key",
         "balance": "/api/account/balance", "usage": "/api/account/key/usage"}
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
    for name, path in PATHS.items():
        req = urllib.request.Request(BASE + path,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET")
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read(32768).decode("utf-8"))
                evidence[name] = {"http_status": response.status, "data": _safe(data)}
        except urllib.error.HTTPError as exc:
            evidence[name] = {"http_status": exc.code, "data": None}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, UnicodeError):
            evidence[name] = {"http_status": None, "data": None}
    identity = evidence.get("identity", {}).get("data")
    subject = identity.get("sub") if isinstance(identity, dict) else None
    return {"state": "EVIDENCE_COLLECTED" if isinstance(subject, str) and subject else "UNKNOWN",
            "provider_subject": subject if isinstance(subject, str) and subject else None,
            "owner_binding": "UNVERIFIED", "spending_authorized": False, "evidence": evidence}
