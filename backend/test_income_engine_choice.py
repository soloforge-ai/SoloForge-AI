import unittest
from dataclasses import replace

from income_engine import (
    OPPORTUNITY_BY_ID,
    OpportunityEvaluation,
    RecommendationResult,
)
from income_engine_choice import PreferenceTradeoffEngine
from test_income_engine import PERSONAS


class _StubRecommendationEngine:
    def __init__(self, base_result, evaluations):
        self.base_result = base_result
        self.evaluations = evaluations

    def recommend(self, user):
        return self.base_result

    def evaluate_opportunity(self, user, opportunity):
        return self.evaluations[opportunity.id]


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

    def test_preference_override_updates_validation_experiment(self):
        preferred_opportunity = OPPORTUNITY_BY_ID["O12"]
        practical_opportunity = OPPORTUNITY_BY_ID["O25"]
        preferred_evaluation = OpportunityEvaluation(
            opportunity_id="O12",
            opportunity_name=preferred_opportunity.name,
            state="ELIGIBLE_PRIMARY",
            fit_score=75.0,
            capability_average=75.0,
            component_scores={
                "revenue_timing_fit": 70.0,
                "acquisition_reachability": 60.0,
                "market_evidence": 75.0,
            },
        )
        practical_evaluation = OpportunityEvaluation(
            opportunity_id="O25",
            opportunity_name=practical_opportunity.name,
            state="ELIGIBLE_PRIMARY",
            fit_score=80.0,
            capability_average=75.0,
            component_scores={
                "revenue_timing_fit": 70.0,
                "acquisition_reachability": 60.0,
                "market_evidence": 75.0,
            },
        )
        base_result = RecommendationResult(
            decision_state="RECOMMEND",
            primary_opportunity="O25",
            fit_score=80.0,
            recommendation_confidence="MEDIUM",
            why_it_fits=["stub practical path"],
            constraints_checked=[],
            assumptions=[],
            alternatives=[],
            rejected_or_demoted=[],
            first_validation_experiment=practical_opportunity.cheap_validation_experiment,
        )
        stub_engine = _StubRecommendationEngine(
            base_result,
            {
                "O12": preferred_evaluation,
                "O25": practical_evaluation,
            },
        )
        engine = PreferenceTradeoffEngine(
            base_engine=stub_engine,
            opportunities=(practical_opportunity, preferred_opportunity),
        )
        user = replace(PERSONAS["p3_visual"], model_preferences=frozenset({"service"}))

        result = engine.recommend(user)

        self.assertEqual("O12", result["primary_opportunity"])
        self.assertEqual(
            preferred_opportunity.cheap_validation_experiment,
            result["first_validation_experiment"],
        )

    def test_productized_service_is_marked_as_service_preference(self):
        opportunity = OPPORTUNITY_BY_ID["O12"]
        evaluation = OpportunityEvaluation(
            opportunity_id="O12",
            opportunity_name=opportunity.name,
            state="ELIGIBLE_PRIMARY",
            fit_score=75.0,
            capability_average=75.0,
            component_scores={},
        )
        user = replace(PERSONAS["p3_visual"], model_preferences=frozenset({"service"}))

        option = PreferenceTradeoffEngine._option_payload(
            role="PREFERENCE_PATH",
            evaluation=evaluation,
            opportunity=opportunity,
            user=user,
        )

        self.assertTrue(option["matches_user_preference"])


if __name__ == "__main__":
    unittest.main()
