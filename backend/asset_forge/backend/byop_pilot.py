"""Internal dispatch scope minted only after the durable one-use pilot claim.

No permit issuance endpoint, environment enable flag, or reusable bearer token.
The database receipt is not a charge receipt. The reservation stays held.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import math
from fastapi import HTTPException
from .byop_ledger import digest

_dispatch = ContextVar("owner_pilot_dispatch", default=None)


def deny():
    raise HTTPException(409, "Owner pilot permit absent, expired, mismatched or already dispatched")


def bound_terms(execution, consent):
    snapshot = execution["snapshot"]
    return {"principal": execution["principal"], "execution_id": execution["id"],
            "credential_id": snapshot["credential_id"], "job_id": snapshot["job_id"],
            "model": snapshot["model"], "consent_id": execution["consent_id"],
            "snapshot_sha256": digest(snapshot), "quote_sha256": digest(consent["quote"]),
            "maximum_micro_pollen": consent["maximum"]}


@contextmanager
def owner_pilot_dispatch(receipt, execution, consent, credential, clock):
    terms = (receipt or {}).get("permit", {})
    expected = bound_terms(execution, consent)
    expires = terms.get("expires_at")
    if (not execution["principal"].startswith("owner:")
            or any(terms.get(k) != v for k, v in expected.items())
            or terms.get("manual_reconciliation_accepted") is not True
            or type(expires) not in (int, float) or not math.isfinite(expires)
            or not clock() < expires <= min(execution["expires_at"], consent["expires_at"])
            or (receipt or {}).get("execution", {}).get("state") != "CALL_STARTED"
            or (receipt or {}).get("execution", {}).get("id") != execution["id"]
            or any((receipt or {}).get("execution", {}).get(k) != execution.get(k)
                   for k in ("principal", "consent_id", "snapshot", "snapshot_sha256", "quote_sha256", "reserved"))
            or credential["principal"] != execution["principal"]):
        deny()
    context = {"snapshot": deepcopy(execution["snapshot"]), "expires_at": expires,
               "token_digest": hashlib.sha256(credential["token"].encode()).hexdigest(),
               "clock": clock, "dispatched": False}
    handle = _dispatch.set(context)
    try:
        yield
    finally:
        context["dispatched"] = True  # cannot escape scope and reuse capability
        _dispatch.reset(handle)


def active():
    return _dispatch.get() is not None


def check_gate():
    context = _dispatch.get()
    if context is None:
        return False
    if context["dispatched"] or context["expires_at"] <= context["clock"]():
        deny()
    return True


def claim_request(prompt, reference, token, settings):
    """Exactly one matching outbound request, including the actual credential."""
    if not active():
        return  # existing non-pilot global gate already denies those paths
    check_gate()
    context = _dispatch.get()
    snap = context["snapshot"]
    if (hashlib.sha256(token.encode()).hexdigest() != context["token_digest"]
            or hashlib.sha256(prompt.encode()).hexdigest() != snap["prompt_sha256"]
            or hashlib.sha256(reference or b"").hexdigest() != snap["reference_sha256"]
            or settings != {"model": snap["model"], "width": snap["settings"]["image_width"],
                            "height": snap["settings"]["image_height"]}):
        deny()
    context["dispatched"] = True
