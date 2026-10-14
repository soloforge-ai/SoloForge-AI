"""Static safety contract for scheduled/manual production smoke.

This test must never make network calls.
"""
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/asset-forge-production-smoke.yml"


class ProductionSmokeSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_no_post_or_generation_execution(self):
        text = self.workflow
        self.assertNotRegex(text, r"(?im)\bcurl\b[^\n]*\s-X\s*(?:POST|PUT|PATCH|DELETE)\b")
        self.assertNotIn("-d '{", text)
        self.assertNotIn("/tmp/generate.json", text)
        self.assertNotIn('"$ASSET_FORGE_BASE_URL/v1/asset-forge/generate"', text)
        self.assertNotIn("local_fallback", text)

    def test_only_health_and_openapi_are_requested(self):
        endpoints = re.findall(r'\$ASSET_FORGE_BASE_URL(/[^"\s]*)', self.workflow)
        self.assertEqual(sorted(endpoints), ["/health", "/openapi.json"])
        self.assertEqual(self.workflow.count("curl -sS"), 2)

    def test_checks_are_read_only_and_do_not_assume_autodeploy(self):
        self.assertNotIn("EXPECTED_GIT_COMMIT", self.workflow)
        self.assertIn("health contract ok", self.workflow)
        self.assertIn("openapi contract ok", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("schedule:", self.workflow)


if __name__ == "__main__":
    unittest.main()
