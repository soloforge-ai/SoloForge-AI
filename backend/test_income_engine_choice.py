import unittest

from income_engine_choice import PreferenceTradeoffEngine
from test_income_engine import PERSONAS


class PreferenceTradeoffEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PreferenceTradeoffEngine()

    def test_visual_product_persona_gets_user_choice(self):
        result = self.engine.recommend(PERSONAS["p3_visual"])

        self.assertEqual("TRADEOFF_CHOICE", result["decision_state"])
        self.assertIsNone(result["primary_opportunity"])
        self.assertEqual("MEDIUM", result["recommendation_confidence"])

        by_role = {item["role"]: item for item in result["tradeoff_options"]}
        self.assertEqual("O26", by_role["PREFERENCE_PATH"]["opportunity_id"])
        self.assertEqual("O13", by_role["REVENUE_PRIORITY_PATH"]["opportunity_id"])

    def test_tradeoff_exposes_structural_differences(self):
        result = self.engine.recommend(PERSONAS["p3_visual"])
        by_role = {item["role"]: item for item in result["tradeoff_options"]}
        preferred = by_role["PREFERENCE_PATH"]
        revenue = by_role["REVENUE_PRIORITY_PATH"]

        self.assertEqual("long", preferred["time_to_first_revenue"])
        self.assertEqual("short", revenue["time_to_first_revenue"])
        self.assertGreater(preferred["execution_fit"], revenue["execution_fit"])
        self.assertGreater(revenue["market_evidence"], preferred["market_evidence"])
        self.assertTrue(any("not income promises" in item for item in result["tradeoff_summary"]))

    def test_matching_preference_keeps_normal_engine_decision(self):
        result = self.engine.recommend(PERSONAS["p1_data"])

        self.assertEqual("TWO_WAY_TEST", result["decision_state"])
        self.assertEqual("O01", result["primary_opportunity"])
        self.assertEqual([], result["tradeoff_options"])

    def test_discovery_state_is_never_overridden_by_preference_layer(self):
        result = self.engine.recommend(PERSONAS["p5_beginner"])

        self.assertEqual("DISCOVERY_REQUIRED", result["decision_state"])
        self.assertIsNone(result["primary_opportunity"])
        self.assertEqual([], result["tradeoff_options"])

    def test_no_confident_match_is_never_overridden_by_preference_layer(self):
        result = self.engine.recommend(PERSONAS["p9_capital_little_time"])

        self.assertEqual("NO_CONFIDENT_MATCH", result["decision_state"])
        self.assertIsNone(result["primary_opportunity"])
        self.assertEqual([], result["tradeoff_options"])


if __name__ == "__main__":
    unittest.main()
