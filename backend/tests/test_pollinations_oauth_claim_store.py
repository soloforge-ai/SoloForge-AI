"""Fail-closed shared claim store contracts. Synthetic transport; no network."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from backend import pollinations_oauth_claim_store as store
from backend import pollinations_oauth_router as router


def test_store_unconfigured_denies_issue_and_consume(monkeypatch):
    monkeypatch.setattr(router, "_supabase_config", lambda: None)
    with pytest.raises(store.ClaimStoreUnavailable):
        store.issue("login_ticket", "synthetic", "owner", {}, 600)
    with pytest.raises(store.ClaimStoreUnavailable):
        store.consume("login_ticket", "synthetic", "owner")


def test_store_outage_and_ambiguous_response_denied(monkeypatch):
    monkeypatch.setattr(router, "_supabase_config", lambda: ("https://example.invalid", "test-only"))
    def outage(*args, **kwargs):
        raise RuntimeError("synthetic outage")
    monkeypatch.setattr(router, "_supabase_request", outage)
    with pytest.raises(store.ClaimStoreUnavailable):
        store.consume("pkce_state", "synthetic", "owner")
    monkeypatch.setattr(router, "_supabase_request", lambda *a, **k: b"not-json")
    with pytest.raises(store.ClaimStoreUnavailable):
        store.consume("pkce_state", "synthetic", "owner")


def test_cross_worker_restart_and_replay_with_shared_synthetic_rpc(monkeypatch):
    """Separate workers use the same durable store, not router dictionaries."""
    monkeypatch.setattr(router, "_supabase_config", lambda: ("https://example.invalid", "test-only"))
    claims = {}
    lock = Lock()
    def fake_rpc(method, path, *, body=None, **kwargs):
        key = (body["p_kind"], body["p_claim_hash"])
        with lock:
            if path.endswith("_issue"):
                if key in claims:
                    raise RuntimeError("duplicate")
                claims[key] = (body["p_owner"], body["p_payload"])
                return b"true"
            item = claims.get(key)
            if item is None or item[0] != body["p_owner"]:
                return b"null"
            claims.pop(key)
            return json.dumps(item[1]).encode()
    monkeypatch.setattr(router, "_supabase_request", fake_rpc)
    store.issue("mobile_handoff", "synthetic-code", "owner", {"session_id": "synthetic-session"}, 120)
    with router._lock:
        router._handoffs.clear()
        router._transactions.clear()
        router._login_tickets.clear()
    assert store.consume("mobile_handoff", "synthetic-code", "other-owner") is None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.consume("mobile_handoff", "synthetic-code", "owner"), range(8)))
    assert results.count({"session_id": "synthetic-session"}) == 1
    assert sum(item is None for item in results) == 7
