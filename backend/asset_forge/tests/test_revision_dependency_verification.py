"""P0-B2 offline-only regression tests; no network, DB or provider."""
import copy
import unittest

from backend.asset_forge.backend.revision_dependency_verification import (
    GRAPHS, verify_revision_chain,
)

H = "a" * 64
def fixture(route="IMAGE"):
    graph = GRAPHS[route]
    ids = {stage: "id-" + stage for stage in graph}
    envelopes, snapshots, revisions = [], {}, {}
    for stage, deps in graph.items():
        dep_ids = [ids[d] for d in deps]
        e = dict(schema_version="1.0", evidence_id=ids[stage],
                 job_id="job", stage=stage, revision_id="rev-" + stage,
                 input_sha256=H, output_sha256=H,
                 artifact_ref="immutable://" + stage, validator_version="v1",
                 result="PASS", reviewer_id="owner",
                 reviewed_at="2026-10-16T00:00:00Z",
                 dependency_evidence_ids=dep_ids)
        envelopes.append(e)
        snapshots[ids[stage]] = {
            **{k: e[k] for k in ("job_id", "revision_id", "stage",
               "input_sha256", "output_sha256", "artifact_ref",
               "reviewer_id", "evidence_id")},
            "verified_upstream_evidence_ids": dep_ids,
        }
        revisions[stage] = e["revision_id"]
    return envelopes, snapshots, revisions

def check(e, s, r, route="IMAGE"):
    return verify_revision_chain(e, route=route, trusted_snapshots=s,
                                 trusted_revision=r)

class ChainTests(unittest.TestCase):
    def test_image_chain(self):
        self.assertEqual(check(*fixture()), "PASS")
    def test_video_chain(self):
        self.assertEqual(check(*fixture("VIDEO"), route="VIDEO"), "PASS")
    def test_route_mismatch(self):
        self.assertEqual(check(*fixture(), route="VIDEO"), "BLOCKED")
    def test_invalid_route(self):
        self.assertEqual(check(*fixture(), route="AUDIO"), "BLOCKED")
    def test_missing_ancestor(self):
        e, s, r = fixture(); e.pop(0)
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_duplicate_stage(self):
        e, s, r = fixture(); e[1] = copy.deepcopy(e[0])
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_duplicate_evidence_id(self):
        e, s, r = fixture(); e[1]["evidence_id"] = e[0]["evidence_id"]
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_cross_job(self):
        e, s, r = fixture(); e[1]["job_id"] = "other"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_wrong_reviewer(self):
        e, s, r = fixture(); e[1]["reviewer_id"] = "attacker"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_stale_revision(self):
        e, s, r = fixture(); r["CONTENT"] = "new"
        self.assertEqual(check(e, s, r), "STALE")
    def test_changed_output_hash(self):
        e, s, r = fixture(); e[1]["output_sha256"] = "b" * 64
        self.assertEqual(check(e, s, r), "STALE")
    def test_changed_input_hash(self):
        e, s, r = fixture(); e[1]["input_sha256"] = "b" * 64
        self.assertEqual(check(e, s, r), "STALE")
    def test_changed_artifact(self):
        e, s, r = fixture(); e[1]["artifact_ref"] = "mutable://new"
        self.assertEqual(check(e, s, r), "STALE")
    def test_changed_snapshot_hash(self):
        e, s, r = fixture(); s[e[1]["evidence_id"]]["output_sha256"] = "b" * 64
        self.assertEqual(check(e, s, r), "STALE")
    def test_replay_from_other_revision(self):
        e, s, r = fixture(); e[1]["revision_id"] = "old"
        self.assertEqual(check(e, s, r), "STALE")
    def test_missing_dependency(self):
        e, s, r = fixture(); e[2]["dependency_evidence_ids"] = []
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_dependency_substitution(self):
        e, s, r = fixture(); e[2]["dependency_evidence_ids"][0] = "id-FORGED"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_cycle(self):
        e, s, r = fixture(); e[0]["dependency_evidence_ids"] = [e[2]["evidence_id"]]
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_unverified_upstream(self):
        e, s, r = fixture(); s[e[2]["evidence_id"]]["verified_upstream_evidence_ids"] = []
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_missing_trusted_snapshot(self):
        e, s, r = fixture(); s.pop(e[0]["evidence_id"])
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_forged_snapshot_reviewer(self):
        e, s, r = fixture(); s[e[1]["evidence_id"]]["reviewer_id"] = "attacker"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_nonpass(self):
        e, s, r = fixture(); e[1]["result"] = "FAIL"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_invalid_hash(self):
        e, s, r = fixture(); e[1]["input_sha256"] = "bad"
        self.assertEqual(check(e, s, r), "STALE")
    def test_invalid_timestamp(self):
        e, s, r = fixture(); e[1]["reviewed_at"] = "bad"
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_missing_trusted_revision(self):
        e, s, r = fixture(); r.pop("CONTENT")
        self.assertEqual(check(e, s, r), "BLOCKED")
    def test_unknown_field(self):
        e, s, r = fixture(); e[1]["allow_publish"] = True
        self.assertEqual(check(e, s, r), "BLOCKED")

if __name__ == "__main__":
    unittest.main()
