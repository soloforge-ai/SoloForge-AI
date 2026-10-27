"""Evidence validator for the existing Ledger.pricing hook; no provider I/O.

The evidence reader is a trusted server dependency, never HTTP request data.
No production reader is installed: default pricing and execution remain locked.
Audited contract: pollinations/pollinations@636c4e4de0bb19a2d13d5c44d08a41004db39da2.
Only the reviewed single-image Kontext contract is supported, not arbitrary models.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
import hashlib
import math
from fastapi import HTTPException
from .byop_ledger import digest

CANONICAL_MODEL = "black-forest-labs/flux.1-kontext-pro"
CONTRACT_REVISION = "636c4e4de0bb19a2d13d5c44d08a41004db39da2"
EVIDENCE_TTL_SECONDS = 30  # SoloForge pilot policy, not a provider guarantee.
MICRO = Decimal(1000000)


def same_reviewed_model(left, right):
    """The documented alias and canonical ID identify the same reviewed model."""
    return left in (CANONICAL_MODEL, "kontext") and right in (CANONICAL_MODEL, "kontext")


def unavailable(reason):
    raise HTTPException(503, reason)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        unavailable("Finite provider pricing/budget evidence required")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        unavailable("Finite provider pricing/budget evidence required")
    if not result.is_finite() or result < 0:
        unavailable("Finite nonnegative provider pricing/budget evidence required")
    return result


def micros(value, rounding):
    return int((value * MICRO).to_integral_value(rounding=rounding))


class EvidencePricing:
    """Offline/server evidence adapter reusing the existing principal ledger.

    Reader returns {principal, credential_id, credential_digest, observed_at,
    catalog, key, balance}. catalog is one /models row; key and balance are the
    same credential's /account/key and /account/balance JSON. The outer binding
    and per-endpoint timestamps must be set by the trusted collector, not the
    provider/client. observed_at contains catalog/key/balance fetch timestamps.
    Account balances, name labels and image bytes alone are never cost evidence.
    """
    def __init__(self, reader, clock):
        self.reader = reader
        self.clock = clock

    def __call__(self, snapshot):
        evidence = self.reader(deepcopy(snapshot))
        if not isinstance(evidence, dict):
            unavailable("Fresh credential-bound provider evidence unavailable")
        now = self.clock()
        observations = evidence.get("observed_at")
        if (not isinstance(observations, dict) or set(observations) != {"catalog", "key", "balance"}
                or any(type(t) not in (int, float) or not math.isfinite(t)
                       or not 0 <= now - t < EVIDENCE_TTL_SECONDS for t in observations.values())):
            unavailable("Provider evidence missing, stale or future-dated")
        observed = min(observations.values())
        if (snapshot.get("operation") != "ceo_image" or snapshot.get("image_count") != 1
                or snapshot.get("model") not in (CANONICAL_MODEL, "kontext")
                or snapshot.get("settings", {}).get("image_width") != 1024
                or snapshot.get("settings", {}).get("image_height") != 1024):
            unavailable("No reviewed maximum price contract for this model/count/dimensions")
        catalog, key, balance = (evidence.get(k) for k in ("catalog", "key", "balance"))
        if not all(isinstance(v, dict) for v in (catalog, key, balance)):
            unavailable("Catalog, key and account evidence all required")
        catalog_id = catalog.get("name", catalog.get("id"))
        if (catalog_id != CANONICAL_MODEL
                or ("id" in catalog and catalog["id"] != catalog_id)
                or catalog.get("community") is not False
                or catalog.get("paid_only") is not False
                or not isinstance(catalog.get("aliases"), list)
                or (snapshot["model"] != CANONICAL_MODEL and "kontext" not in catalog["aliases"])
                or any(catalog.get(k) for k in ("pricing_variants", "pricing_units", "pricing_adjustments"))):
            unavailable("Unreviewed model, pricing variant, unit or adjustment")
        endpoints = catalog.get("supported_endpoints")
        if not isinstance(endpoints, list) or "/v1/images/edits" not in endpoints:
            unavailable("Catalog does not verify the required image-edit endpoint")
        health = catalog.get("health")
        # Pilot policy: historical health is necessary evidence, not a promise
        # of availability or permission for this credential at dispatch time.
        if not isinstance(health, dict) or health.get("status") != "healthy":
            unavailable("Healthy model evidence unavailable; pilot quote denied")
        pricing = catalog.get("pricing")
        if (not isinstance(pricing, dict) or set(pricing) != {"currency", "completionImageTokens"}
                or pricing["currency"] != "pollen"):
            unavailable("Complete fixed per-image Pollen price required")
        rate = number(pricing["completionImageTokens"])
        # Audited public price is cost .04 × multiplier .75; never treat .04
        # upstream cost as public price, or silently accept changed rate sheets.
        if rate != Decimal("0.03"):
            unavailable("Provider rate changed; reviewed contract update required")
        if (key.get("valid") is not True or key.get("type") != "secret"
                or not key.get("id") or not key.get("userId")
                or type(key.get("questPollenOnly")) is not bool
                or "byopApp" not in key):
            unavailable("Verified secret-key identity and funding restrictions required")
        permissions = key.get("permissions", {})
        models = permissions.get("models") if isinstance(permissions, dict) else []
        if models is not None and (not isinstance(models, list)
                or not {"image", CANONICAL_MODEL}.intersection(models)):
            unavailable("Selected key does not permit the requested model")
        if "models" not in permissions:
            unavailable("Provider key model restrictions unavailable")
        try:
            expiry_date = datetime.fromisoformat(key["expiresAt"].replace("Z", "+00:00"))
            if expiry_date.tzinfo is None:
                raise ValueError("Timezone required")
            expiry = expiry_date.timestamp()
        except (KeyError, TypeError, ValueError, AttributeError):
            unavailable("A finite provider key expiry is required for the pilot")
        if not math.isfinite(expiry) or expiry <= now:
            unavailable("Provider key is expired")
        app = key["byopApp"]
        if app is not None and (not isinstance(app, dict) or not app.get("clientKeyId") or not app.get("appUser")):
            unavailable("App attribution incomplete; maximum markup unavailable")
        markup = Decimal("0") if app is None or app["appUser"] == key["userId"] else Decimal("0.25")
        amount = micros(rate * (1 + markup), ROUND_CEILING)
        # null is unlimited in the provider contract; the pilot intentionally
        # requires a finite key budget. balance alone may be a key budget.
        key_budget = micros(number(key.get("pollenBudget")), ROUND_FLOOR)
        visible_budget = micros(number(balance.get("balance")), ROUND_FLOOR)
        account = balance.get("accountBalance")
        if not isinstance(account, dict):
            unavailable("Independent account funding buckets unavailable; account:usage evidence required")
        tier, paid = (micros(number(account.get(k)), ROUND_FLOOR) for k in ("tier", "paid"))
        # Provider does not split a request across buckets. Never add them.
        funding = tier if key["questPollenOnly"] else max(tier, paid)
        if min(key_budget, visible_budget, funding) < amount:
            raise HTTPException(409, "Selected key budget or one eligible account bucket is insufficient")
        if (evidence.get("credential_id") != snapshot["credential_id"]
                or not isinstance(evidence.get("credential_digest"), str)
                or len(evidence["credential_digest"]) != 64
                or not str(evidence.get("principal", "")).startswith("owner:")):
            unavailable("Owner and exact credential evidence binding required")
        return {
            "basis": "Pollinations fixed single-image Kontext contract " + CONTRACT_REVISION,
            "includes_all_charges": True, "maximum_micro_pollen": amount,
            "base_micro_pollen": micros(rate, ROUND_CEILING),
            "markup_upper_percent": int(markup * 100), "earnings_confirmed": False,
            "expires_at": min(observed + EVIDENCE_TTL_SECONDS, expiry),
            "observed_at": observed, "principal": evidence["principal"],
            "credential_id": snapshot["credential_id"], "credential_digest": evidence["credential_digest"],
            "provider_key_id": key["id"], "provider_subject": key["userId"],
            "snapshot_sha256": digest(snapshot), "contract_revision": CONTRACT_REVISION,
            "catalog_model_id": catalog_id,
            "catalog_publisher": catalog.get("publisher"),  # Never an inference-provider selector.
            "available_micro_pollen": min(key_budget, visible_budget, funding),
        }

    def validate_context(self, principal, snapshot, quote, credential):
        if (not principal.startswith("owner:") or quote.get("principal") != principal
                or quote.get("credential_id") != snapshot["credential_id"]
                or quote.get("snapshot_sha256") != digest(snapshot)
                or not credential or credential.get("principal") != principal
                or credential.get("verification_status") != "VERIFIED"
                or credential.get("provider_ownership_verified") is not True
                or credential.get("provider_subject") != quote.get("provider_subject")
                or hashlib.sha256(credential["token"].encode()).hexdigest() != quote.get("credential_digest")):
            unavailable("Quote is not bound to the authenticated owner and selected verified credential")

    def validate_dispatch(self, principal, snapshot, quote, credential, held):
        if quote.get("expires_at", 0) <= self.clock():
            unavailable("Quote expired before CALL_STARTED; fresh consent required")
        self.validate_context(principal, snapshot, quote, credential)
        current = self(snapshot)  # local trusted reader only; never a generation/retry.
        self.validate_context(principal, snapshot, current, credential)
        stable = ("principal", "credential_id", "credential_digest", "provider_key_id", "provider_subject",
                  "snapshot_sha256", "contract_revision", "base_micro_pollen", "maximum_micro_pollen", "markup_upper_percent")
        if any(quote.get(k) != current.get(k) for k in stable):
            unavailable("Pricing or credential evidence changed; fresh consent required")
        if current["available_micro_pollen"] < held:
            raise HTTPException(409, "Provider budget cannot cover all held principal reservations")
