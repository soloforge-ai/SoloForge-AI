"""Security tests: no synthetic production trust or KMS bypass."""
import unittest
from backend.asset_forge.backend.trusted_qa_production_gate import (
    production_trust_admitted, production_qa_authorized, REQUIRED,
)

class ProductionGateTests(unittest.TestCase):
    def test_missing_authority(self):
        self.assertFalse(production_trust_admitted(None))
    def test_claimed_all_true_is_not_identity(self):
        payload={k: True for k in REQUIRED}
        self.assertFalse(production_trust_admitted(payload))
    def test_claimed_kms_is_not_key_custody(self):
        payload={k: True for k in REQUIRED}
        payload.update(key_source="KMS",key_state="ACTIVE",
                       key_algorithm="HMAC-SHA256",key_id="prod")
        self.assertFalse(production_trust_admitted(payload))
    def test_production_execution_never_authorized_by_fixtures(self):
        self.assertFalse(production_qa_authorized(identity=object(),
                         keys=object(),transaction=object()))
