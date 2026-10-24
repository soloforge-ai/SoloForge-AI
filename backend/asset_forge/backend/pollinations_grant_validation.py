"""Provider metadata verification only. Does not authorize provider spending."""
import json
import math
import urllib.request
from datetime import datetime, timezone

class GrantVerificationError(RuntimeError):
    pass

def _read(url, token):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise GrantVerificationError("Invalid provider response")
            raw = response.read(65537)
            if len(raw) > 65536:
                raise GrantVerificationError("Oversized provider response")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise GrantVerificationError("Invalid provider metadata")
            return data
    except (OSError, ValueError) as exc:
        raise GrantVerificationError("Provider metadata unavailable") from exc

def verify_provider_token(token, *, client_id, trusted_app_key_id):
    if (not isinstance(token, str) or not token.strip()
        or not isinstance(client_id, str) or not client_id.startswith("pk_")
        or not isinstance(trusted_app_key_id, str) or not trusted_app_key_id.strip()
        or trusted_app_key_id != trusted_app_key_id.strip()
        or trusted_app_key_id.startswith(("pk_", "sk_"))):
        raise GrantVerificationError("Invalid trusted application configuration")
    userinfo = _read("https://enter.pollinations.ai/api/oauth/userinfo", token)
    key = _read("https://gen.pollinations.ai/account/key", token)
    sub, owner, byop = userinfo.get("sub"), key.get("userId"), key.get("byopApp")
    if (not isinstance(sub, str) or not sub.strip() or not isinstance(owner, str) or not owner.strip()
        or sub != owner
        or key.get("valid") is not True or key.get("type") != "secret"
        or not isinstance(byop, dict) or byop.get("clientKeyId") != trusted_app_key_id):
        raise GrantVerificationError("Provider identity or app mismatch")
    expiry, expiry_string = key.get("expiresIn"), key.get("expiresAt")
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or expiry <= 0 or not isinstance(expiry_string, str):
        raise GrantVerificationError("Invalid key expiry")
    try:
        expiry_at = datetime.fromisoformat(expiry_string.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GrantVerificationError("Invalid expiry timestamp") from exc
    if expiry_at.tzinfo is None or expiry_at <= datetime.now(timezone.utc):
        raise GrantVerificationError("Expired key")
    budget = key.get("pollenBudget")
    if type(budget) not in (int, float) or not math.isfinite(budget) or budget <= 0:
        raise GrantVerificationError("Invalid or depleted budget")
    models = key.get("permissions", {}).get("models") if isinstance(key.get("permissions"), dict) else None
    if not isinstance(models, list) or not models or any(not isinstance(m, str) or not m for m in models):
        raise GrantVerificationError("Invalid model restrictions")
    return {"provider_subject": sub, "key_owner": owner, "key_id": key.get("id"),
            "internal_app_key_id": trusted_app_key_id, "key_expires_at": int(expiry_at.timestamp()),
            "status": "METADATA_VERIFIED_SPENDING_BLOCKED"}
