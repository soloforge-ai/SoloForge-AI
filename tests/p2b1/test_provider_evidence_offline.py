"""Negative tests for OFFLINE synthetic evidence only."""
import hmac
import pytest
from backend.asset_forge.security.provider_evidence_offline import (
    canonical, verify_offline_fixture, EvidenceRejected,
)
KEY = b"fixture-only-key-not-a-provider-credential-0001"
DATA = dict(kind="RESULT", owner_id="owner-1", session_id="session-1",
            subject_id="wallet-1", provider_request_id="req-1",
            authorization_id="allocation-1", outcome="SUCCEEDED", pollen="1.25")
EXPECTED = dict(expected_kind="RESULT", expected_owner="owner-1",
                expected_session="session-1", expected_subject="wallet-1",
                expected_provider_request="req-1", expected_authorization="allocation-1")

def envelope(payload=None):
    p = DATA.copy() if payload is None else payload
    return {"payload": p, "signature": hmac.digest(KEY, canonical(p), "sha256").hex()}

def verify(env, **changes):
    return verify_offline_fixture(env, trusted_test_key=KEY, **(EXPECTED | changes))

def test_verified_offline_fixture():
    result = verify(envelope())
    assert result.outcome == "SUCCEEDED"
    assert len(result.digest) == 64

@pytest.mark.parametrize("field,wrong", [
    ("owner_id","other-owner"), ("session_id","other-session"),
    ("subject_id","other-wallet"), ("provider_request_id","other-request"),
    ("authorization_id","other-allocation"), ("kind","WALLET"),
])
def test_reject_wrong_binding(field,wrong):
    with pytest.raises(EvidenceRejected):
        verify(envelope(), **{dict(kind="expected_kind",owner_id="expected_owner",
           session_id="expected_session",subject_id="expected_subject",
           provider_request_id="expected_provider_request",
           authorization_id="expected_authorization")[field]: wrong})

def test_reject_tampering():
    env=envelope()
    env["payload"]["pollen"]="0"
    with pytest.raises(EvidenceRejected):
        verify(env)

def test_reject_forged_key():
    env=envelope()
    env["signature"]=hmac.digest(b"attacker-controlled-key-000000000000000",canonical(env["payload"]),"sha256").hex()
    with pytest.raises(EvidenceRejected):
        verify(env)

@pytest.mark.parametrize("bad", ["UNKNOWN_RECONCILE","CALL_STARTED","PENDING"])
def test_reject_ambiguous_result(bad):
    with pytest.raises(EvidenceRejected):
        verify(envelope(DATA | {"outcome":bad}))

@pytest.mark.parametrize("bad", ["-1","NaN","Infinity","invalid"])
def test_reject_invalid_amount(bad):
    with pytest.raises(EvidenceRejected):
        verify(envelope(DATA | {"pollen":bad}))

def test_reject_missing_fields():
    p=DATA.copy()
    del p["provider_request_id"]
    with pytest.raises(EvidenceRejected):
        verify(envelope(p))

def test_reject_attacker_supplied_key():
    env=envelope()
    env["key"]=KEY.hex()
    with pytest.raises(EvidenceRejected):
        verify(env)
