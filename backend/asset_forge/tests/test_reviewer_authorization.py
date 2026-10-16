"""P0-B3.1 pure offline reviewer authorization negative security tests."""
import copy
import unittest

from backend.asset_forge.backend.reviewer_authorization import authorize_reviewer


def fixture():
    return dict(
        trusted_principal=dict(
            principal_id="owner-1", authenticated=True,
            session_expires_at="2026-10-17T00:00:00Z",
        ),
        trusted_grant=dict(
            principal_id="owner-1", job_id="job-1",
            allowed_stages=["CONTENT", "VISUAL"],
            revision_id="rev-1", expires_at="2026-10-17T00:00:00Z",
            revoked=False,
        ),
        trusted_target=dict(
            job_id="job-1", stage="VISUAL", revision_id="rev-1",
        ),
        evaluated_at="2026-10-16T00:00:00Z",
    )


class ReviewerAuthorizationTests(unittest.TestCase):
    def check(self, args):
        return authorize_reviewer(**args)

    def test_authorized_owner_fixture(self):
        self.assertEqual(self.check(fixture()), "PASS")

    def test_unknown_reviewer(self):
        x = fixture(); x["trusted_principal"]["principal_id"] = "stranger"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_unauthenticated_principal(self):
        x = fixture(); x["trusted_principal"]["authenticated"] = False
        self.assertEqual(self.check(x), "BLOCKED")

    def test_truthy_string_authentication(self):
        x = fixture(); x["trusted_principal"]["authenticated"] = "true"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_expired_session(self):
        x = fixture(); x["evaluated_at"] = x["trusted_principal"]["session_expires_at"]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_expired_grant(self):
        x = fixture(); x["evaluated_at"] = x["trusted_grant"]["expires_at"]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_revoked_grant(self):
        x = fixture(); x["trusted_grant"]["revoked"] = True
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_revocation_field(self):
        x = fixture(); del x["trusted_grant"]["revoked"]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_truthy_revocation_string(self):
        x = fixture(); x["trusted_grant"]["revoked"] = "false"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_cross_job(self):
        x = fixture(); x["trusted_target"]["job_id"] = "job-2"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_cross_stage(self):
        x = fixture(); x["trusted_target"]["stage"] = "FINAL_QA"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_stale_revision(self):
        x = fixture(); x["trusted_target"]["revision_id"] = "rev-2"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_forged_principal_field(self):
        x = fixture(); x["trusted_principal"]["reviewer_id"] = "attacker"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_forged_grant_role(self):
        x = fixture(); x["trusted_grant"]["role"] = "admin"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_extra_execution_permission(self):
        x = fixture(); x["trusted_target"]["allow_generation"] = True
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_principal(self):
        x = fixture(); x["trusted_principal"] = None
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_grant(self):
        x = fixture(); x["trusted_grant"] = None
        self.assertEqual(self.check(x), "BLOCKED")

    def test_missing_target(self):
        x = fixture(); x["trusted_target"] = None
        self.assertEqual(self.check(x), "BLOCKED")

    def test_empty_allowed_stages(self):
        x = fixture(); x["trusted_grant"]["allowed_stages"] = []
        self.assertEqual(self.check(x), "BLOCKED")

    def test_duplicate_stages(self):
        x = fixture(); x["trusted_grant"]["allowed_stages"] = ["VISUAL", "VISUAL"]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_unknown_stage_in_grant(self):
        x = fixture(); x["trusted_grant"]["allowed_stages"] = ["VISUAL", "PUBLISH"]
        self.assertEqual(self.check(x), "BLOCKED")

    def test_unknown_target_stage(self):
        x = fixture(); x["trusted_target"]["stage"] = "PUBLISH"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_malformed_clock(self):
        x = fixture(); x["evaluated_at"] = "tomorrow"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_malformed_session_expiry(self):
        x = fixture(); x["trusted_principal"]["session_expires_at"] = "bad"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_malformed_grant_expiry(self):
        x = fixture(); x["trusted_grant"]["expires_at"] = "bad"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_untrusted_principal_identifier(self):
        x = fixture(); x["trusted_principal"]["principal_id"] = " "
        self.assertEqual(self.check(x), "BLOCKED")

    def test_untrusted_grant_identifier(self):
        x = fixture(); x["trusted_grant"]["job_id"] = ""
        self.assertEqual(self.check(x), "BLOCKED")

    def test_exact_boundary_before_expiry(self):
        x = fixture(); x["evaluated_at"] = "2026-10-16T23:59:59Z"
        self.assertEqual(self.check(x), "PASS")

    def test_session_grant_independent(self):
        x = fixture()
        x["trusted_principal"]["session_expires_at"] = "2026-10-18T00:00:00Z"
        x["trusted_grant"]["expires_at"] = "2026-10-15T00:00:00Z"
        self.assertEqual(self.check(x), "BLOCKED")

    def test_does_not_mutate_fixture(self):
        x = fixture(); original = copy.deepcopy(x)
        self.assertEqual(self.check(x), "PASS")
        self.assertEqual(x, original)


if __name__ == "__main__":
    unittest.main()
