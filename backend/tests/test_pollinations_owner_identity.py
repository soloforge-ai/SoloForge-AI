"""Offline-only contract tests. Provider metadata is monkeypatched; no network."""
import unittest
from unittest.mock import patch

from backend import pollinations_grant_validation as grant

USER = {"sub": "owner-123"}
KEY = {"userId": "owner-123", "valid": True, "type": "secret", "id": "key-1",
       "byopApp": {"clientKeyId": "internal-app"}, "expiresIn": 3600,
       "expiresAt": "2099-01-01T00:00:00Z", "pollenBudget": 5,
       "permissions": {"models": ["image"]}}

class OwnerIdentityTests(unittest.TestCase):
    def verify(self, user=None, key=None):
        with patch.object(grant, "_read", side_effect=[USER if user is None else user,
                                                        KEY if key is None else key]) as read:
            result = grant.verify_provider_token("fake-token", client_id="pk_fake",
                                                 trusted_app_key_id="internal-app")
            self.assertEqual(read.call_count, 2)
            return result

    def test_matching_owner_accepted(self):
        self.assertEqual(self.verify()["provider_subject"], "owner-123")

    def test_mismatched_owner_denied(self):
        with self.assertRaises(grant.GrantVerificationError):
            self.verify(key={**KEY, "userId": "other-owner"})

    def test_missing_userinfo_subject_denied(self):
        with self.assertRaises(grant.GrantVerificationError):
            self.verify(user={})

    def test_missing_key_owner_denied(self):
        with self.assertRaises(grant.GrantVerificationError):
            self.verify(key={**KEY, "userId": None})

    def test_wrong_app_denied(self):
        with self.assertRaises(grant.GrantVerificationError):
            self.verify(key={**KEY, "byopApp": {"clientKeyId": "other-app"}})

    def test_expired_key_denied(self):
        with self.assertRaises(grant.GrantVerificationError):
            self.verify(key={**KEY, "expiresIn": 0})

if __name__ == "__main__":
    unittest.main()
