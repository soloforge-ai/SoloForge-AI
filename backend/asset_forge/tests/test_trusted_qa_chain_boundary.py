"""Negative tests for trusted caller and whole-chain claim boundary."""
import unittest
from backend.asset_forge.backend.trusted_qa_chain_boundary import authorize_chain_once
from backend.asset_forge.tests.test_trusted_qa_full_chain import trusted
from backend.asset_forge.tests.test_offline_qa_issuance import NOW

class AuthorityWrapper:
    def __init__(self):
        self.a,self.signed=trusted("IMAGE")
        self.claims=0
        self.allowed=True
    def authenticated_internal_caller(self):
        return self.allowed
    def load_chain(self,route,ids):
        return self.a.load_chain(route,ids)
    def read_immutable_artifact(self,ref):
        return self.a.read_immutable_artifact(ref)
    def claim_chain_atomic(self,**kwargs):
        self.claims+=1
        return self.claims==1

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.b=AuthorityWrapper()
    def check(self):
        return authorize_chain_once(authority=self.b,attestations=self.b.signed,
                                    route="IMAGE",claim_id="claim-1",evaluated_at=NOW)
    def test_success_is_advisory(self):
        self.assertEqual(self.check(),"PASS")
    def test_replay(self):
        self.assertEqual(self.check(),"PASS")
        self.assertEqual(self.check(),"BLOCKED")
    def test_unauthenticated(self):
        self.b.allowed=False
        self.assertEqual(self.check(),"BLOCKED")
        self.assertEqual(self.b.claims,0)
    def test_revoked_reviewer(self):
        self.b.a.reviewers["e-CONTENT"]["grant"]["revoked"]=True
        self.assertEqual(self.check(),"BLOCKED")
        self.assertEqual(self.b.claims,0)
    def test_tampered_output(self):
        self.b.a.artifacts["immutable:CONTENT"]=b"tampered"
        self.assertEqual(self.check(),"BLOCKED")
    def test_no_authority(self):
        self.assertEqual(authorize_chain_once(authority=None,attestations=[],
                         route="IMAGE",claim_id="x",evaluated_at=NOW),"BLOCKED")
    def test_claim_failure(self):
        self.b.claim_chain_atomic=lambda **kw: False
        self.assertEqual(self.check(),"BLOCKED")
    def test_claim_exception(self):
        def fail(**kw): raise OSError("db unavailable")
        self.b.claim_chain_atomic=fail
        self.assertEqual(self.check(),"BLOCKED")
