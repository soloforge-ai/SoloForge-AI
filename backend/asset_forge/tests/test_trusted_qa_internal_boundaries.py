"""Negative tests for unwired production identity and key custody boundaries."""
import unittest
from backend.asset_forge.backend.trusted_qa_internal_identity import (
    InternalPrincipal, authenticate_internal, ISSUER, AUDIENCE, SERVICE,
)
from backend.asset_forge.backend.trusted_qa_key_custody import (
    KeyMetadata, sign_qa_evidence, SupabaseVaultSigningAdapter,
)
from backend.asset_forge.backend.trusted_qa_production_gate import production_qa_authorized

NOW = 2000000000

class Verifier:
    def __init__(self, principal): self.principal = principal
    def verify(self, credential, *, issuer, audience):
        if credential != "verified-workload-proof": return None
        return self.principal

class Signer:
    def __init__(self, state="ACTIVE", algorithm="Ed25519"):
        self.state, self.algorithm = state, algorithm
        self.calls = 0
    def metadata(self):
        return KeyMetadata("qa-v1", self.algorithm, self.state, NOW - 1, NOW + 60)
    def sign(self, payload, *, key_id):
        self.calls += 1
        return b"x" * 64

class SecurityBoundaries(unittest.TestCase):
    def setUp(self):
        self.principal = InternalPrincipal(SERVICE, ISSUER, AUDIENCE, NOW + 60)
    def test_unconfigured_verifier_denies(self):
        self.assertIsNone(authenticate_internal(credential="anything", verifier=None, now=NOW))
    def test_client_supplied_owner_and_provider_tokens_denied(self):
        v = Verifier(self.principal)
        for credential in ("Bearer owner-session", "supabase-service-role", "pollinations-oauth", ""):
            self.assertIsNone(authenticate_internal(credential=credential, verifier=v, now=NOW))
    def test_wrong_service_issuer_audience_expiry_denied(self):
        for p in (
            InternalPrincipal("attacker", ISSUER, AUDIENCE, NOW+60),
            InternalPrincipal(SERVICE, "untrusted", AUDIENCE, NOW+60),
            InternalPrincipal(SERVICE, ISSUER, "wrong", NOW+60),
            InternalPrincipal(SERVICE, ISSUER, AUDIENCE, NOW),
            InternalPrincipal(SERVICE, ISSUER, AUDIENCE, NOW+301),
        ):
            self.assertIsNone(authenticate_internal(
                credential="verified-workload-proof", verifier=Verifier(p), now=NOW))
    def test_valid_verifier_is_not_production_authority(self):
        p = authenticate_internal(credential="verified-workload-proof",
                                  verifier=Verifier(self.principal), now=NOW)
        self.assertEqual(p, self.principal)
        self.assertFalse(production_qa_authorized(identity=p))
    def test_missing_or_vault_signer_denied(self):
        self.assertIsNone(sign_qa_evidence(principal=self.principal, signer=None, payload=b"e", now=NOW))
        self.assertIsNone(sign_qa_evidence(principal=self.principal,
            signer=SupabaseVaultSigningAdapter(), payload=b"e", now=NOW))
    def test_revoked_verify_only_wrong_algorithm_denied_without_signing(self):
        for state, alg in (("REVOKED","Ed25519"),("VERIFY_ONLY","Ed25519"),("ACTIVE","HMAC-SHA256")):
            s = Signer(state, alg)
            self.assertIsNone(sign_qa_evidence(principal=self.principal, signer=s,
                                               payload=b"e", now=NOW))
            self.assertEqual(s.calls, 0)
    def test_expired_identity_and_non_bytes_denied(self):
        s = Signer()
        expired = InternalPrincipal(SERVICE, ISSUER, AUDIENCE, NOW)
        self.assertIsNone(sign_qa_evidence(principal=expired, signer=s, payload=b"e", now=NOW))
        self.assertIsNone(sign_qa_evidence(principal=self.principal, signer=s, payload="e", now=NOW))
        self.assertEqual(s.calls, 0)
    def test_mock_signer_not_production_custody(self):
        s = Signer()
        self.assertEqual(sign_qa_evidence(principal=self.principal, signer=s,
                                          payload=b"canonical", now=NOW), ("qa-v1", b"x"*64))
        self.assertFalse(production_qa_authorized(identity=self.principal, keys=s))
        self.assertEqual(s.calls, 1)
