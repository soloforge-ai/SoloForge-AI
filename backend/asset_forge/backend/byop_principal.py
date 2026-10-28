"""Shared BYOP principals. Existing owner-only guards remain untouched."""
from dataclasses import dataclass
import json
import os
from uuid import UUID
import urllib.request
from fastapi import HTTPException
from .owner_v2 import OwnerV2, Unauthorized, Unavailable
from .shared_supabase import supabase_request
from .soloforge_session import bearer_token


@dataclass(frozen=True)
class Principal:
    kind: str
    id: str

    @property
    def key(self):
        return f"{self.kind}:{self.id}"


def require_generation_role(principal: Principal) -> None:
    """Pilot eligibility only; never replaces consent, pricing or execution locks."""
    if principal.kind != "owner":
        raise HTTPException(403, "Member generation is disabled pending separate authorization")


def authenticate(authorization: str | None) -> Principal:
    token = bearer_token(authorization)
    if not token:
        raise HTTPException(401, "Application authentication required")
    if token.startswith("sf_owner_v2_"):
        try:
            return Principal("owner", OwnerV2().authenticate(authorization)["owner_id"])
        except Unauthorized:
            raise HTTPException(401, "Owner authentication required") from None
        except Unavailable:
            raise HTTPException(503, "Identity authority unavailable") from None
    # Never interpret a legacy application bearer as a member or owner.
    if token.startswith("v2."):
        raise HTTPException(401, "Supabase member authentication required")
    try:
        base = os.environ["SUPABASE_URL"].rstrip("/")
        key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
        request = urllib.request.Request(base + "/auth/v1/user", headers={
            "Authorization": "Bearer " + token, "apikey": key})
        with urllib.request.urlopen(request, timeout=10) as response:
            user = json.loads(response.read(65536))
        uid = str(UUID(user["id"]))
        if user.get("is_anonymous") is not False:
            raise ValueError("Non-anonymous identity required")
    except Exception:
        raise HTTPException(401, "Member authentication unavailable or invalid") from None
    principal = Principal("member", uid)
    require_active(principal)
    return principal


def require_active(principal: Principal) -> None:
    if principal.kind == "owner":
        return  # OwnerV2 authentication already checked the live registry/session.
    if principal.kind != "member":
        raise HTTPException(403, "Unknown principal")
    try:
        uid = str(UUID(principal.id))
        rows = supabase_request("GET", "soloforge_memberships?user_id=eq." + uid
                                + "&status=eq.ACTIVE&select=user_id&limit=1")
    except Exception:
        raise HTTPException(503, "Membership authority unavailable") from None
    if not rows:
        raise HTTPException(403, "Active membership required")
