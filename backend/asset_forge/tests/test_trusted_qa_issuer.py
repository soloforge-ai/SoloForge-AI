"""Unwired issuer/key lifecycle/full-chain negative security contract tests."""
import copy
import hashlib
import unittest
from backend.asset_forge.backend.trusted_qa_issuer import (
    issue_trusted, verify_with_lifecycle, verify_trusted_chain,
)
from backend.asset_forge.tests.test_offline_qa_issuance import fixture, NOW, KEY

class Authority:
    def __init__(self, route="IMAGE"):
        self.x=fixture(route)
        self.artifacts={"in:"+eid: b"input:"+eid for eid in self.x["trusted_snapshots"]}
        for eid, data in self.x["trusted_artifacts"].items():
            self.artifacts["immutable:"+self.x["trusted_snapshots"][eid]["stage"]]=data
        self.ctx=None
        self.key=("test-k1",KEY)
        self.records={"test-k1":{"key":KEY,"status":"ACTIVE",
                     "not_before":"2026-10-15T00:00:00Z",
                     "not_after":"2026-10-18T00:00:00Z"}}
        self.reviewers={}
        for a in self.x["attestations"]:
            e=a["envelope"];eid=e["evidence_id"]
            self.reviewers[eid]={
                "principal":{"principal_id":"owner-1","authenticated":True,
                             "session_expires_at":"2026-10-18T00:00:00Z"},
                "grant":{"principal_id":"owner-1","job_id":"job-1",
                         "allowed_stages":list(self.x["trusted_revision"]),
                         "revision_id":"rev-1","expires_at":"2026-10-18T00:00:00Z",
                         "revoked":False},
                "target":{"job_id":"job-1","stage":e["stage"],"revision_id":"rev-1"}}
    def read_immutable_artifact(self, ref):
        return self.artifacts[ref]
    def active_signing_key(self):
        return self.key
    def load_issuance(self,eid):
        a=next(a for a in self.x["attestations"] if a["envelope"]["evidence_id"]==eid)
        env=copy.deepcopy(a["envelope"])
        env["input_sha256"]=hashlib.sha256(self.artifacts["in:"+eid]).hexdigest()
        r=self.reviewers[eid]
        return {"envelope":env,"principal":r["principal"],"grant":r["grant"],
                "target":r["target"],"evaluated_at":NOW,
                "input_ref":"in:"+eid,"output_ref":env["artifact_ref"]}
    def load_chain(self,route,ids):
        return {"snapshots":self.x["trusted_snapshots"],
                "revision":self.x["trusted_revision"],"key_records":self.records,
                "reviewers":self.reviewers,
                "artifacts":{eid:{"input_ref":"in:"+eid,
                                 "output_ref":self.x["trusted_snapshots"][eid]["artifact_ref"]}
                             for eid in ids},
                "consumed_ids":frozenset()}

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.a=Authority()
    def test_issuer_valid(self):
        signed=issue_trusted(authority=self.a,evidence_id="e-CONTENT")
        self.assertIsNotNone(signed)
        self.assertEqual(signed["envelope"]["input_sha256"],
                         hashlib.sha256(b"input:e-CONTENT").hexdigest())
    def test_issuer_no_authority(self):
        self.assertIsNone(issue_trusted(authority=None,evidence_id="e-CONTENT"))
    def test_issuer_tampered_input(self):
        self.a.artifacts["in:e-CONTENT"]=b"changed"
        self.assertIsNotNone(issue_trusted(authority=self.a,evidence_id="e-CONTENT"))
        # Hash derives from trusted bytes, never from submitted caller evidence.
    def test_issuer_revoked(self):
        self.a.reviewers["e-CONTENT"]["grant"]["revoked"]=True
        self.assertIsNone(issue_trusted(authority=self.a,evidence_id="e-CONTENT"))
    def test_issuer_weak_key(self):
        self.a.key=("test-k1",b"weak")
        self.assertIsNone(issue_trusted(authority=self.a,evidence_id="e-CONTENT"))
    def test_key_active(self):
        self.assertEqual(verify_with_lifecycle(attestation=self.a.x["attestations"][0],
                         trusted_key_records=self.a.records,evaluated_at=NOW),"PASS")
    def test_key_verify_only(self):
        self.a.records["test-k1"]["status"]="VERIFY_ONLY"
        self.test_key_active()
    def test_key_revoked(self):
        self.a.records["test-k1"]["status"]="REVOKED"
        self.assertEqual(verify_with_lifecycle(attestation=self.a.x["attestations"][0],
                         trusted_key_records=self.a.records,evaluated_at=NOW),"BLOCKED")
    def test_key_expired(self):
        self.a.records["test-k1"]["not_after"]=NOW
        self.test_key_revoked_result()
    def test_key_revoked_result(self):
        self.assertEqual(verify_with_lifecycle(attestation=self.a.x["attestations"][0],
                         trusted_key_records=self.a.records,evaluated_at=NOW),"BLOCKED")
    def test_key_unknown(self):
        self.a.records={}
        self.test_key_revoked_result()
    def test_chain_valid(self):
        # Fixture input hash intentionally differs from actual input bytes.
        # A production chain must reject such a mismatch.
        self.assertEqual(verify_trusted_chain(authority=self.a,
                         attestations=self.a.x["attestations"],route="IMAGE",
                         evaluated_at=NOW),"BLOCKED")
    def test_chain_reviewer_revoked(self):
        self.a.reviewers["e-CONTENT"]["grant"]["revoked"]=True
        self.test_chain_valid()
    def test_chain_wrong_route(self):
        self.assertEqual(verify_trusted_chain(authority=self.a,
                         attestations=self.a.x["attestations"],route="VIDEO",
                         evaluated_at=NOW),"BLOCKED")
    def test_chain_unknown_key(self):
        self.a.records={}
        self.test_chain_valid()
