"""Per-principal durable consent/reservation ledger. No provider dispatch here.

All money uses integer micro-Pollen. A quote must come from a trusted server
pricing authority, never the requesting client. Production pricing is unavailable
in V1, so quote acquisition fails closed. Offline tests supply a fake authority.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import time
from uuid import uuid4
from fastapi import HTTPException
from .shared_supabase import supabase_request


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def unavailable_pricing(*args, **kwargs):
    raise HTTPException(503, "Documented model-specific maximum Pollen pricing unavailable")


class SupabaseLedger:
    def read(self, principal):
        from urllib.parse import quote
        rows = supabase_request("GET", "byop_ledgers?principal=eq." + quote(principal, safe="")
                                + "&select=revision,state&limit=1")
        if not rows:
            raise HTTPException(503, "Principal budget has not been provisioned")
        return rows[0]["revision"], rows[0]["state"]

    def cas(self, principal, revision, state):
        return supabase_request("POST", "rpc/byop_ledger_cas", {
            "p_principal": principal, "p_revision": revision, "p_state": state}) is True


class Ledger:
    def __init__(self, store=None, pricing=unavailable_pricing, clock=time.time):
        self.store = store or SupabaseLedger()
        self.pricing = pricing
        self.clock = clock

    def change(self, principal, action):
        for _ in range(8):
            revision, state = self.store.read(principal)
            state = deepcopy(state)
            result = action(state)
            if self.store.cas(principal, revision, state):
                return result
        raise HTTPException(409, "Concurrent ledger update; no provider call started")

    def consent(self, principal, snapshot, maximum, expires_at):
        now = self.clock()
        if type(maximum) is not int or maximum <= 0 or not now < expires_at <= now + 600:
            raise HTTPException(400, "Invalid consent bound or expiry")
        required = {"credential_id", "job_id", "revision", "operation", "model",
                    "image_count", "prompt_sha256", "reference_sha256", "settings"}
        if set(snapshot) != required or snapshot["operation"] != "ceo_image" or snapshot["image_count"] != 1:
            raise HTTPException(400, "Exact single-image CEO snapshot required")
        quote = self.pricing(deepcopy(snapshot))
        if (not isinstance(quote, dict) or type(quote.get("maximum_micro_pollen")) is not int
                or not 0 < quote["maximum_micro_pollen"] <= maximum
                or not quote.get("basis") or quote.get("expires_at", 0) <= now):
            raise HTTPException(409, "Trusted pricing does not fit consent")
        consent_id = str(uuid4())
        record = {"principal": principal, "snapshot": deepcopy(snapshot),
                  "snapshot_sha256": digest(snapshot), "maximum": maximum,
                  "quote": quote, "expires_at": min(expires_at, quote["expires_at"]),
                  "created_at": now, "used": False}
        def add(state):
            state.setdefault("consents", {})[consent_id] = record
            return {"consent_id": consent_id, **record}
        return self.change(principal, add)

    def reserve(self, principal, consent_id, execution_id):
        # The caller supplies a stable UUID for duplicates; it cannot select an
        # execution in another principal's ledger.
        from uuid import UUID
        try:
            execution_id = str(UUID(execution_id))
        except (ValueError, TypeError):
            raise HTTPException(400, "Execution UUID required") from None
        def reserve(state):
            executions = state.setdefault("executions", {})
            if execution_id in executions:
                current = executions[execution_id]
                if current["consent_id"] != consent_id:
                    raise HTTPException(409, "Execution identifier already bound")
                return deepcopy(current)
            consent = state.get("consents", {}).get(consent_id)
            if not consent or consent["used"] or consent["expires_at"] <= self.clock():
                raise HTTPException(409, "Consent absent, expired or consumed")
            active = [e for e in executions.values() if e["state"] in
                      {"RESERVED", "CALL_STARTED", "UNKNOWN", "GENERATED"}]
            reserved = sum(e["reserved"] for e in active)
            if len(active) >= state.get("concurrency_limit", 1):
                raise HTTPException(409, "Principal execution limit reached")
            amount = consent["quote"]["maximum_micro_pollen"]
            if amount + reserved + state.get("settled", 0) > state.get("budget", 0):
                raise HTTPException(409, "Principal budget exhausted")
            consent["used"] = True
            execution = {"id": execution_id, "consent_id": consent_id,
                         "principal": principal, "snapshot": deepcopy(consent["snapshot"]),
                         "snapshot_sha256": consent["snapshot_sha256"],
                         "reserved": amount, "state": "RESERVED",
                         "expires_at": consent["expires_at"], "created_at": self.clock()}
            executions[execution_id] = execution
            return deepcopy(execution)
        return self.change(principal, reserve)

    def start(self, principal, execution_id, snapshot):
        def start(state):
            execution = state.get("executions", {}).get(execution_id)
            if (not execution or execution["state"] != "RESERVED"
                    or execution["expires_at"] <= self.clock()
                    or execution["snapshot_sha256"] != digest(snapshot)):
                raise HTTPException(409, "Execution cannot be dispatched or replayed")
            execution.update(state="CALL_STARTED", started_at=self.clock())
            return deepcopy(execution)
        return self.change(principal, start)

    def outcome(self, principal, execution_id, generated=False, asset=None):
        def finish(state):
            execution = state.get("executions", {}).get(execution_id)
            if not execution or execution["state"] != "CALL_STARTED":
                raise HTTPException(409, "Outcome requires an unreconciled started call")
            execution.update(state="GENERATED" if generated else "UNKNOWN", asset=asset)
            # Even a valid image is not proof of the amount charged. Keep the
            # reservation until separately evidenced operator reconciliation.
            return deepcopy(execution)
        return self.change(principal, finish)
