"""P0-B4 fail-closed integration preparation; offline injected backend only."""
import copy
import hashlib
import hmac
import unittest
from backend.asset_forge.backend.trusted_qa_server import verify_and_claim
from backend.asset_forge.backend.offline_qa_issuance import canonical_bytes
from backend.asset_forge.tests.test_offline_qa_issuance import fixture, NOW

class Backend:
    def __init__(self):
        base = fixture()
        self.signed = copy.deepcopy(base["attestations"][0])
        env = self.signed["envelope"]
        self.artifacts = {"immutable:input": b"input", "immutable:output": b"artifact:CONTENT"}
        env["input_sha256"] = hashlib.sha256(self.artifacts["immutable:input"]).hexdigest()
        body = {k: self.signed[k] for k in ("scheme", "key_id", "envelope")}
        self.signed["signature"] = hmac.new(base["trusted_keys"]["test-k1"],
                                            canonical_bytes(body), hashlib.sha256).hexdigest()
        self.context = {
            "trusted_principal": {"principal_id": "owner-1", "authenticated": True,
                                  "session_expires_at": "2026-10-18T00:00:00Z"},
            "trusted_grant": {"principal_id": "owner-1", "job_id": "job-1",
                              "allowed_stages": ["CONTENT"], "revision_id": "rev-1",
                              "expires_at": "2026-10-18T00:00:00Z", "revoked": False},
            "trusted_target": {"job_id": "job-1", "stage": "CONTENT", "revision_id": "rev-1"},
            "evaluated_at": NOW,
            "trusted_keys": base["trusted_keys"],
            "expected_envelope": copy.deepcopy(env),
            "input_artifact_ref": "immutable:input",
            "input_sha256": env["input_sha256"],
            "output_artifact_ref": "immutable:output",
            "output_sha256": env["output_sha256"],
        }
        self.claimed = set()
        self.calls = 0

    def load_context(self, eid):
        return self.context

    def read_immutable_artifact(self, ref):
        return self.artifacts[ref]

    def claim_once(self, eid, claim_id, job, rev, stage, principal):
        self.calls += 1
        if eid in self.claimed:
            return False
        self.claimed.add(eid)
        return True

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.signed = copy.deepcopy(self.backend.signed)

    def verify(self):
        return verify_and_claim(backend=self.backend, attestation=self.signed, claim_id="claim-1")

    def test_happy_path_advisory(self):
        self.assertEqual(self.verify(), "PASS")
        self.assertEqual(self.backend.calls, 1)

    def test_replay(self):
        self.assertEqual(self.verify(), "PASS")
        self.assertEqual(self.verify(), "BLOCKED")

    def test_no_backend(self):
        self.assertEqual(verify_and_claim(backend=None, attestation=self.signed,
                                          claim_id="claim-1"), "BLOCKED")

    def test_no_claim_id(self):
        self.assertEqual(verify_and_claim(backend=self.backend, attestation=self.signed,
                                          claim_id=""), "BLOCKED")

    def test_tampered_envelope(self):
        self.signed["envelope"]["job_id"] = "attacker"
        self.assertEqual(self.verify(), "BLOCKED")
        self.assertEqual(self.backend.calls, 0)

    def test_tampered_signature(self):
        self.signed["signature"] = "0" * 64
        self.assertEqual(self.verify(), "BLOCKED")

    def test_cross_job_snapshot(self):
        self.backend.context["expected_envelope"]["job_id"] = "other"
        self.assertEqual(self.verify(), "BLOCKED")

    def test_revoked(self):
        self.backend.context["trusted_grant"]["revoked"] = True
        self.assertEqual(self.verify(), "BLOCKED")

    def test_expired_grant(self):
        self.backend.context["trusted_grant"]["expires_at"] = NOW
        self.assertEqual(self.verify(), "BLOCKED")

    def test_expired_session(self):
        self.backend.context["trusted_principal"]["session_expires_at"] = NOW
        self.assertEqual(self.verify(), "BLOCKED")

    def test_unknown_key(self):
        self.backend.context["trusted_keys"] = {}
        self.assertEqual(self.verify(), "BLOCKED")

    def test_input_bytes_tampered(self):
        self.backend.artifacts["immutable:input"] = b"wrong"
        self.assertEqual(self.verify(), "BLOCKED")

    def test_output_bytes_tampered(self):
        self.backend.artifacts["immutable:output"] = b"wrong"
        self.assertEqual(self.verify(), "BLOCKED")

    def test_missing_input(self):
        del self.backend.artifacts["immutable:input"]
        self.assertEqual(self.verify(), "BLOCKED")

    def test_missing_output(self):
        del self.backend.artifacts["immutable:output"]
        self.assertEqual(self.verify(), "BLOCKED")

    def test_storage_exception(self):
        self.backend.load_context = lambda _: (_ for _ in ()).throw(OSError())
        self.assertEqual(self.verify(), "BLOCKED")

    def test_claim_exception(self):
        self.backend.claim_once = lambda *a: (_ for _ in ()).throw(OSError())
        self.assertEqual(self.verify(), "BLOCKED")

    def test_missing_context(self):
        del self.backend.context["trusted_keys"]
        self.assertEqual(self.verify(), "BLOCKED")

    def test_reviewer_mismatch(self):
        self.backend.context["trusted_principal"]["principal_id"] = "attacker"
        self.assertEqual(self.verify(), "BLOCKED")

    def test_not_authenticated(self):
        self.backend.context["trusted_principal"]["authenticated"] = False
        self.assertEqual(self.verify(), "BLOCKED")

    def test_no_mutation_on_block(self):
        self.backend.context["trusted_grant"]["revoked"] = True
        before = copy.deepcopy(self.signed)
        self.assertEqual(self.verify(), "BLOCKED")
        self.assertEqual(self.signed, before)
        self.assertEqual(self.backend.calls, 0)
