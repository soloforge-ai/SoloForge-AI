import unittest

from income_engine import CapabilityEvidence as CE
from income_engine import OPPORTUNITIES, RecommendationEngine, UserProfile


def profile(
    user_id,
    urgency,
    hours,
    schedule,
    budget,
    loss,
    devices,
    caps,
    work_modes,
    interaction,
    camera=False,
    voice=False,
    distribution=(),
    models=("service",),
    skill_confidence="medium",
    diagnostic_mode="standard",
    constraints=(),
):
    return UserProfile(
        user_id=user_id,
        revenue_urgency=urgency,
        available_hours_weekly=hours,
        schedule_consistency=schedule,
        starting_budget_thb=budget,
        maximum_loss_tolerance_thb=loss,
        devices=frozenset(devices),
        capabilities={k: CE(v, f"fixture evidence for {k}") for k, v in caps.items()},
        preferred_work_modes=frozenset(work_modes),
        customer_interaction_tolerance=interaction,
        camera_tolerance=camera,
        voice_tolerance=voice,
        distribution_assets=frozenset(distribution),
        model_preferences=frozenset(models),
        skill_confidence=skill_confidence,
        diagnostic_mode=diagnostic_mode,
        constraints=frozenset(constraints),
    )


PERSONAS = {
    "p1_data": profile(
        "p1_data", "within_30_days", 16, "high", 500, 500,
        {"windows", "android"},
        {
            "spreadsheet": "PROVEN", "attention_detail": "PROVEN", "data_reasoning": "PROVEN",
            "dashboard": "SIGNAL", "stakeholder_clarification": "SIGNAL", "document_handling": "SIGNAL",
            "structured_data": "PROVEN", "research": "SIGNAL", "qualification_judgment": "SIGNAL",
        },
        {"organizing_data", "structured_problem_solving"}, "medium",
        distribution={"professional_network"}, models={"service"}, skill_confidence="high",
    ),
    "p2_speaker": profile(
        "p2_speaker", "within_30_days", 28, "high", 1000, 1000,
        {"android", "production_phone"},
        {
            "customer_interaction": "PROVEN", "sales_resilience": "PROVEN", "communication": "PROVEN",
            "explanation": "PROVEN", "subject_knowledge": "UNKNOWN", "content_consistency": "SIGNAL",
            "video_editing": "SIGNAL", "storytelling_pacing": "SIGNAL", "visual_qa": "SIGNAL",
        },
        {"speaking", "selling", "support", "content"}, "high", camera=True, voice=True,
        distribution={"direct_outreach", "creator_community"}, models={"service", "content_commission"}, skill_confidence="high",
    ),
    "p3_visual": profile(
        "p3_visual", "within_3_months", 21, "high", 500, 500,
        {"ipad", "android"},
        {
            "production_quality": "PROVEN", "niche_relevance": "SIGNAL", "packaging": "SIGNAL", "distribution": "SIGNAL",
            "workflow_design": "SIGNAL", "visual_design": "PROVEN",
        },
        {"visual_design", "product_building"}, "low",
        distribution={"creator_community"}, models={"product"}, skill_confidence="high",
    ),
    "p4_seller": profile(
        "p4_seller", "within_30_days", 14, "high", 3000, 3000,
        {"windows", "android"},
        {
            "operational_discipline": "PROVEN", "platform_familiarity": "PROVEN", "customer_communication": "PROVEN",
            "communication": "PROVEN", "process_discipline": "PROVEN", "patience": "SIGNAL",
            "copy_research": "SIGNAL", "product_understanding": "PROVEN",
        },
        {"operations", "support", "selling"}, "high", voice=True,
        distribution={"ecommerce_community", "professional_network", "owned_audience"}, models={"service"}, skill_confidence="high",
    ),
    "p5_beginner": profile(
        "p5_beginner", "within_30_days", 28, "high", 0, 0,
        {"android"}, {}, {"not_sure"}, "medium",
        models={"not_sure"}, skill_confidence="low", diagnostic_mode="skill_discovery",
    ),
    "p6_student": profile(
        "p6_student", "within_3_months", 16, "high", 100, 100,
        {"windows", "android"},
        {
            "visual_organization": "PROVEN", "document_tools": "PROVEN", "attention_detail": "SIGNAL",
            "explanation": "SIGNAL", "subject_knowledge": "SIGNAL", "customer_interaction": "SIGNAL",
            "visual_design": "SIGNAL", "canva": "SIGNAL",
        },
        {"writing", "visual_design", "structured_tasks"}, "medium", voice=True,
        distribution={"education_community"}, models={"service"}, skill_confidence="medium",
    ),
    "p7_worker": profile(
        "p7_worker", "within_3_months", 7, "medium", 1000, 1000,
        {"windows", "android"},
        {
            "visual_organization": "PROVEN", "document_tools": "PROVEN", "attention_detail": "SIGNAL",
            "reliability": "PROVEN", "organization": "PROVEN", "written_communication": "SIGNAL",
        },
        {"writing", "structured_tasks", "organizing_data"}, "low",
        distribution={"professional_network"}, models={"service"}, skill_confidence="medium",
    ),
    "p8_unemployed": profile(
        "p8_unemployed", "within_7_days", 56, "high", 300, 300,
        {"windows", "android"},
        {
            "reliability": "PROVEN", "organization": "PROVEN", "written_communication": "PROVEN",
            "communication": "PROVEN", "patience": "PROVEN", "process_discipline": "PROVEN",
            "customer_interaction": "PROVEN", "sales_resilience": "SIGNAL",
        },
        {"operations", "support", "research"}, "high", voice=True,
        distribution={"professional_network", "direct_outreach"}, models={"service"}, skill_confidence="medium",
    ),
    "p9_capital_little_time": profile(
        "p9_capital_little_time", "over_3_months", 3, "low", 20000, 20000,
        {"windows", "android", "ipad"},
        {
            "organization": "PROVEN", "reliability": "SIGNAL", "written_communication": "SIGNAL",
            "process_mapping": "SIGNAL", "customer_interaction": "SIGNAL",
        },
        {"planning", "evaluating", "delegating"}, "medium",
        distribution={"professional_network"}, models={"not_sure"}, skill_confidence="medium",
    ),
    "p10_phone_ops": profile(
        "p10_phone_ops", "within_7_days", 70, "high", 0, 0,
        {"android"},
        {
            "communication": "PROVEN", "patience": "SIGNAL", "process_discipline": "PROVEN",
            "reliability": "PROVEN", "organization": "SIGNAL", "written_communication": "SIGNAL",
            "consistency": "PROVEN", "instruction_following": "PROVEN", "qa": "SIGNAL", "attention_detail": "SIGNAL",
        },
        {"support", "operations", "repetitive_operations"}, "high", voice=True,
        distribution={"direct_outreach"}, models={"service", "platform_work"}, skill_confidence="medium",
    ),
}


class IncomeEngineP4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine()

    def test_library_has_28_unique_opportunities(self):
        self.assertEqual(28, len(OPPORTUNITIES))
        self.assertEqual(28, len({o.id for o in OPPORTUNITIES}))

    def test_p1_data_prefers_spreadsheet_cleanup(self):
        result = self.engine.recommend(PERSONAS["p1_data"])
        self.assertEqual("TWO_WAY_TEST", result.decision_state)
        self.assertEqual("O01", result.primary_opportunity)

    def test_p2_speaker_prefers_outreach_support(self):
        result = self.engine.recommend(PERSONAS["p2_speaker"])
        self.assertEqual("TWO_WAY_TEST", result.decision_state)
        self.assertEqual("O07", result.primary_opportunity)

    def test_p3_visual_exposes_weight_calibration_result(self):
        result = self.engine.recommend(PERSONAS["p3_visual"])
        self.assertEqual("RECOMMEND", result.decision_state)
        self.assertEqual("O13", result.primary_opportunity)
        alternative_ids = {item["opportunity_id"] for item in result.alternatives}
        self.assertIn("O26", alternative_ids)

    def test_p4_seller_prefers_store_operations(self):
        result = self.engine.recommend(PERSONAS["p4_seller"])
        self.assertEqual("TWO_WAY_TEST", result.decision_state)
        self.assertEqual("O16", result.primary_opportunity)

    def test_p5_beginner_requires_discovery(self):
        result = self.engine.recommend(PERSONAS["p5_beginner"])
        self.assertEqual("DISCOVERY_REQUIRED", result.decision_state)
        self.assertIsNone(result.primary_opportunity)

    def test_p6_student_prefers_document_formatting(self):
        result = self.engine.recommend(PERSONAS["p6_student"])
        self.assertEqual("RECOMMEND", result.decision_state)
        self.assertEqual("O08", result.primary_opportunity)

    def test_p7_worker_prefers_asynchronous_document_work(self):
        result = self.engine.recommend(PERSONAS["p7_worker"])
        self.assertEqual("RECOMMEND", result.decision_state)
        self.assertEqual("O08", result.primary_opportunity)

    def test_p8_unemployed_prefers_virtual_admin(self):
        result = self.engine.recommend(PERSONAS["p8_unemployed"])
        self.assertEqual("TWO_WAY_TEST", result.decision_state)
        self.assertEqual("O04", result.primary_opportunity)

    def test_p9_capital_only_returns_no_confident_match(self):
        result = self.engine.recommend(PERSONAS["p9_capital_little_time"])
        self.assertEqual("NO_CONFIDENT_MATCH", result.decision_state)
        self.assertIsNone(result.primary_opportunity)

    def test_p10_phone_ops_prefers_customer_support(self):
        result = self.engine.recommend(PERSONAS["p10_phone_ops"])
        self.assertEqual("TWO_WAY_TEST", result.decision_state)
        self.assertEqual("O05", result.primary_opportunity)

    def test_urgent_user_does_not_get_distribution_long_horizon_default(self):
        user = PERSONAS["p10_phone_ops"]
        by_id = {o.id: o for o in OPPORTUNITIES}
        for opportunity_id in ("O27", "O28"):
            evaluation = self.engine.evaluate_opportunity(user, by_id[opportunity_id])
            self.assertNotEqual("ELIGIBLE_PRIMARY", evaluation.state)

    def test_fit_score_is_structured_and_experiment_is_returned(self):
        result = self.engine.recommend(PERSONAS["p1_data"])
        self.assertIsInstance(result.fit_score, float)
        self.assertTrue(result.first_validation_experiment)
        self.assertGreaterEqual(len(result.why_it_fits), 3)


if __name__ == "__main__":
    unittest.main()
