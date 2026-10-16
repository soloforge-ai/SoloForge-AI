"""Offline QA foundation security and negative-path regression tests."""
import copy
import hashlib
import unittest
from backend.asset_forge.backend.offline_qa_issuance import (
    artifact_sha256, audit_record, canonical_bytes, issue_attestation,
    verify_attestation, verify_artifacts, verify_offline_chain,
)
from backend.asset_forge.backend.revision_dependency_verification import GRAPHS

KEY = b"offline-test-only-shared-key-at-least-32-bytes"
NOW = "2026-10-16T00:00:00Z"


def fixture(route="IMAGE"):
    graph = GRAPHS[route]
    ids = {stage: "e-" + stage for stage in graph}
    principal = {"principal_id": "owner-1", "authenticated": True,
                 "session_expires_at": "2026-10-18T00:00:00Z"}
    grant = {"principal_id": "owner-1", "job_id": "job-1",
             "allowed_stages": list(graph), "revision_id": "rev-1",
             "expires_at": "2026-10-18T00:00:00Z", "revoked": False}
    result = dict(attestations=[], route=route, trusted_snapshots={},
                  trusted_revision={}, trusted_artifacts={},
                  trusted_keys={"test-k1": KEY}, consumed_evidence_ids=frozenset())
    for stage, deps in graph.items():
        data = ("artifact:" + stage).encode()
        eid = ids[stage]
        env = dict(schema_version="1.0", evidence_id=eid, job_id="job-1",
                   stage=stage, revision_id="rev-1", input_sha256="a" * 64,
                   output_sha256=hashlib.sha256(data).hexdigest(),
                   artifact_ref="immutable:" + stage, validator_version="offline-1",
                   result="PASS", reviewer_id="owner-1", reviewed_at=NOW,
                   dependency_evidence_ids=[ids[x] for x in deps])
        target = {"job_id": "job-1", "stage": stage, "revision_id": "rev-1"}
        signed = issue_attestation(envelope=env, trusted_principal=principal,
                                   trusted_grant=grant, trusted_target=target,
                                   evaluated_at=NOW, key_id="test-k1", signing_key=KEY)
        result["attestations"].append(signed)
        snapshot = {k: env[k] for k in ("job_id", "revision_id", "stage",
                    "input_sha256", "output_sha256", "artifact_ref", "reviewer_id", "evidence_id")}
        snapshot["verified_upstream_evidence_ids"] = list(env["dependency_evidence_ids"])
        result["trusted_snapshots"][eid] = snapshot
        result["trusted_artifacts"][eid] = data
        result["trusted_revision"][stage] = "rev-1"
    return result


class OfflineQASecurityTests(unittest.TestCase):
    def check(self, x):
        return verify_offline_chain(**x)

    def test_image_pass(self):
        self.assertEqual(self.check(fixture()), "PASS")

    def test_video_pass(self):
        self.assertEqual(self.check(fixture("VIDEO")), "PASS")

    def test_valid_signature(self):
        x = fixture()
        self.assertEqual(verify_attestation(attestation=x["attestations"][0],
                                            trusted_keys=x["trusted_keys"]), "PASS")

    def test_signature_tamper(self):
        x = fixture(); x["attestations"][0]["signature"] = "0" * 64
        self.assertEqual(self.check(x), "BLOCKED")

    def test_envelope_tamper(self):
        x = fixture(); x["attestations"][0]["envelope"]["reviewer_id"] = "attacker"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_signature(self):
        x = fixture(); x["attestations"][0].pop("signature")
        self.assertEqual(self.check(x), "BLOCKED")

    def test_extra_signature_field(self):
        x = fixture(); x["attestations"][0]["allow_execution"] = True
        self.assertEqual(self.check(x), "BLOCKED")

    def test_unknown_key(self):
        x = fixture(); x["trusted_keys"] = {}
        self.assertEqual(self.check(x), "BLOCKED")

    def test_wrong_key(self):
        x = fixture(); x["trusted_keys"] = {"test-k1": b"x" * 32}
        self.assertEqual(self.check(x), "BLOCKED")

    def test_key_id_tamper(self):
        x = fixture(); x["attestations"][0]["key_id"] = "wrong"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_replay(self):
        x = fixture(); x["consumed_evidence_ids"] = frozenset({"e-CONTENT"})
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_replay_fixture(self):
        x = fixture(); x["consumed_evidence_ids"] = None
        self.assertEqual(self.check(x), "BLOCKED")

    def test_tampered_artifact(self):
        x = fixture(); x["trusted_artifacts"]["e-CONTENT"] = b"tampered"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_artifact(self):
        x = fixture(); x["trusted_artifacts"].pop("e-CONTENT")
        self.assertEqual(self.check(x), "BLOCKED")

    def test_nonbytes_artifact(self):
        x = fixture(); x["trusted_artifacts"]["e-CONTENT"] = "artifact:CONTENT"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_changed_snapshot_hash(self):
        x = fixture(); x["trusted_snapshots"]["e-CONTENT"]["output_sha256"] = "0" * 64
        self.assertEqual(self.check(x), "BLOCKED")

    def test_cross_job_snapshot(self):
        x = fixture(); x["trusted_snapshots"]["e-CONTENT"]["job_id"] = "other"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_extra_snapshot_field(self):
        x = fixture(); x["trusted_snapshots"]["e-CONTENT"]["allow_execution"] = True
        self.assertEqual(self.check(x), "BLOCKED")

    def test_stale_revision(self):
        x = fixture(); x["trusted_revision"]["CONTENT"] = "rev-2"
        self.assertEqual(self.check(x), "STALE")

    def test_wrong_route(self):
        x = fixture(); x["route"] = "VIDEO"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_unknown_route(self):
        x = fixture(); x["route"] = "PUBLISH"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_dependency_tamper(self):
        x = fixture(); x["attestations"][-1]["envelope"]["dependency_evidence_ids"] = []
        self.assertEqual(self.check(x), "BLOCKED")

    def test_duplicate_attestation(self):
        x = fixture(); x["attestations"][1] = x["attestations"][0]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_canonical_order(self):
        self.assertEqual(canonical_bytes({"b": 2, "a": 1}),
                         canonical_bytes({"a": 1, "b": 2}))

    def test_canonical_reject_float(self):
        self.assertIsNone(canonical_bytes({"a": 1.0}))

    def test_canonical_reject_tuple(self):
        self.assertIsNone(canonical_bytes({"a": (1,)}))

    def test_artifact_hash(self):
        self.assertEqual(artifact_sha256(b"abc"), hashlib.sha256(b"abc").hexdigest())

    def test_audit_record(self):
        x = fixture()
        a = audit_record(attestation=x["attestations"][0], decision="PASS", evaluated_at=NOW)
        self.assertEqual(a["evidence_id"], "e-CONTENT")
        self.assertNotIn("signature", a)

    def test_invalid_audit_decision(self):
        x = fixture()
        self.assertIsNone(audit_record(attestation=x["attestations"][0],
                                       decision="PUBLISH", evaluated_at=NOW))

    def test_no_mutation(self):
        x = fixture(); before = copy.deepcopy(x)
        self.assertEqual(self.check(x), "PASS")
        self.assertEqual(x, before)

    def test_revoked_reviewer_cannot_issue(self):
        x = fixture(); env = x["attestations"][0]["envelope"]
        p = {"principal_id": "owner-1", "authenticated": True,
             "session_expires_at": "2026-10-18T00:00:00Z"}
        g = {"principal_id": "owner-1", "job_id": "job-1",
             "allowed_stages": ["CONTENT"], "revision_id": "rev-1",
             "expires_at": "2026-10-18T00:00:00Z", "revoked": True}
        t = {"job_id": "job-1", "stage": "CONTENT", "revision_id": "rev-1"}
        self.assertIsNone(issue_attestation(envelope=env, trusted_principal=p,
                          trusted_grant=g, trusted_target=t, evaluated_at=NOW,
                          key_id="test-k1", signing_key=KEY))

    def test_weak_key_cannot_issue(self):
        x = fixture(); env = x["attestations"][0]["envelope"]
        p = {"principal_id": "owner-1", "authenticated": True,
             "session_expires_at": "2026-10-18T00:00:00Z"}
        g = {"principal_id": "owner-1", "job_id": "job-1",
             "allowed_stages": ["CONTENT"], "revision_id": "rev-1",
             "expires_at": "2026-10-18T00:00:00Z", "revoked": False}
        t = {"job_id": "job-1", "stage": "CONTENT", "revision_id": "rev-1"}
        self.assertIsNone(issue_attestation(envelope=env, trusted_principal=p,
                          trusted_grant=g, trusted_target=t, evaluated_at=NOW,
                          key_id="test-k1", signing_key=b"short"))
