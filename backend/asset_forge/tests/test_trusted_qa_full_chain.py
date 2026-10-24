"""Positive and adversarial IMAGE/VIDEO trusted route chain tests."""
import copy
import hashlib
import unittest
from backend.asset_forge.backend.offline_qa_issuance import issue_attestation
from backend.asset_forge.backend.trusted_qa_issuer import verify_trusted_chain
from backend.asset_forge.tests.test_trusted_qa_issuer import Authority
from backend.asset_forge.tests.test_offline_qa_issuance import NOW, KEY

def trusted(route):
    a=Authority(route)
    signed=[]
    for old in a.x["attestations"]:
        env=copy.deepcopy(old["envelope"])
        eid=env["evidence_id"]
        env["input_sha256"]=hashlib.sha256(a.artifacts["in:"+eid]).hexdigest()
        a.x["trusted_snapshots"][eid]["input_sha256"]=env["input_sha256"]
        r=a.reviewers[eid]
        signed.append(issue_attestation(envelope=env,
                      trusted_principal=r["principal"],trusted_grant=r["grant"],
                      trusted_target=r["target"],evaluated_at=NOW,
                      key_id="test-k1",signing_key=KEY))
    return a,signed

class FullChainTests(unittest.TestCase):
    def check(self,a,signed,route):
        return verify_trusted_chain(authority=a,attestations=signed,
                                    route=route,evaluated_at=NOW)
    def test_image_full_chain_pass(self):
        a,s=trusted("IMAGE")
        self.assertEqual(self.check(a,s,"IMAGE"),"PASS")
    def test_video_full_chain_pass(self):
        a,s=trusted("VIDEO")
        self.assertEqual(self.check(a,s,"VIDEO"),"PASS")
    def test_input_tamper(self):
        a,s=trusted("IMAGE")
        a.artifacts["in:e-CONTENT"]=b"tampered"
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_output_tamper(self):
        a,s=trusted("IMAGE")
        a.artifacts["immutable:CONTENT"]=b"tampered"
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_revoked_reviewer(self):
        a,s=trusted("IMAGE")
        a.reviewers["e-CONTENT"]["grant"]["revoked"]=True
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_key_retired(self):
        a,s=trusted("IMAGE")
        a.records["test-k1"]["status"]="REVOKED"
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_replay(self):
        a,s=trusted("IMAGE")
        load=a.load_chain
        def consumed(route,ids):
            ctx=load(route,ids)
            ctx["consumed_ids"]=frozenset({"e-CONTENT"})
            return ctx
        a.load_chain=consumed
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_stale_revision(self):
        a,s=trusted("IMAGE")
        a.x["trusted_revision"]["CONTENT"]="rev-new"
        self.assertEqual(self.check(a,s,"IMAGE"),"STALE")
    def test_dependency_tamper(self):
        a,s=trusted("IMAGE")
        s[-1]["envelope"]["dependency_evidence_ids"]=[]
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
    def test_cross_job(self):
        a,s=trusted("IMAGE")
        a.x["trusted_snapshots"]["e-CONTENT"]["job_id"]="other"
        self.assertEqual(self.check(a,s,"IMAGE"),"BLOCKED")
