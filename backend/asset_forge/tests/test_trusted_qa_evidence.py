"""P0-B1 offline negative security tests; no network, DB or providers."""
import unittest
from backend.asset_forge.backend.trusted_qa_evidence import verify_evidence

H = "a" * 64
def envelope(stage="CONTENT", evidence_id="e1", dependencies=None):
    return dict(schema_version="1.0", evidence_id=evidence_id, job_id="job1",
                stage=stage, revision_id="rev1", input_sha256=H,
                output_sha256=H, artifact_ref="immutable://a",
                validator_version="v1", result="PASS", reviewer_id="owner",
                reviewed_at="2026-10-16T00:00:00Z",
                dependency_evidence_ids=dependencies or [])

def snapshot(e, stages=None, upstream_ids=None):
    return {**{k: e[k] for k in ("job_id","revision_id","stage","input_sha256",
             "output_sha256","artifact_ref","reviewer_id","evidence_id")},
            "required_stages": stages if stages is not None else [],
            "verified_upstream_evidence_ids": upstream_ids if upstream_ids is not None else []}

class EvidenceTests(unittest.TestCase):
    def test_valid_root(self):
        e = envelope()
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e)), "PASS")
    def test_missing_snapshot(self):
        self.assertEqual(verify_evidence(envelope(), trusted_snapshot=None), "BLOCKED")
    def test_forged_reviewer(self):
        e = envelope(); e["reviewer_id"] = "attacker"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(envelope())), "BLOCKED")
    def test_forged_hash(self):
        e = envelope(); e["output_sha256"] = "b" * 64
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(envelope())), "BLOCKED")
    def test_invalid_hash(self):
        e = envelope(); e["output_sha256"] = "a"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e)), "BLOCKED")
    def test_stale_revision(self):
        e = envelope(); e["revision_id"] = "old"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(envelope())), "BLOCKED")
    def test_forged_artifact(self):
        e = envelope(); e["artifact_ref"] = "mutable://x"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(envelope())), "BLOCKED")
    def test_missing_dependency(self):
        e = envelope("GROUNDING")
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"])), "BLOCKED")
    def test_valid_dependency(self):
        root = envelope()
        e = envelope("GROUNDING", "e2", ["e1"])
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"], ["e1"]),
                                         upstream=[root]), "PASS")
    def test_unverified_dependency(self):
        root = envelope()
        e = envelope("GROUNDING", "e2", ["e1"])
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"]),
                                         upstream=[root]), "BLOCKED")
    def test_duplicate_dependency(self):
        e = envelope("GROUNDING", "e2", ["e1", "e1"])
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"], ["e1"]),
                                         upstream=[envelope()]), "BLOCKED")
    def test_cross_job_dependency(self):
        root = envelope(); root["job_id"] = "other"
        e = envelope("GROUNDING", "e2", ["e1"])
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"], ["e1"]),
                                         upstream=[root]), "BLOCKED")
    def test_cross_revision_dependency(self):
        root = envelope(); root["revision_id"] = "old"
        e = envelope("GROUNDING", "e2", ["e1"])
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT"], ["e1"]),
                                         upstream=[root]), "BLOCKED")
    def test_fake_result(self):
        e = envelope(); e["result"] = "REVIEW_REQUIRED"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e)), "BLOCKED")
    def test_unknown_field(self):
        e = envelope(); e["authorized_to_publish"] = True
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e)), "BLOCKED")
    def test_bad_timestamp(self):
        e = envelope(); e["reviewed_at"] = "yesterday"
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e)), "BLOCKED")
    def test_malformed_input(self):
        self.assertEqual(verify_evidence(None, trusted_snapshot={}), "BLOCKED")
    def test_no_final_pass_without_dependencies(self):
        e = envelope("FINAL_QA")
        self.assertEqual(verify_evidence(e, trusted_snapshot=snapshot(e, ["CONTENT", "GROUNDING", "VISUAL"])), "BLOCKED")

if __name__ == "__main__":
    unittest.main()
