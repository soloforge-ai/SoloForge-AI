from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CAPABILITY_VALUES = {
    "PROVEN": 100.0,
    "SIGNAL": 65.0,
    "UNKNOWN": 25.0,
    "CONTRADICTED": 0.0,
}

COST_MAX_THB = {
    "zero": 0,
    "very_low": 500,
    "low": 2_000,
    "moderate": 10_000,
    "capital_required": 50_000,
}

TIMING_FIT = {
    "within_7_days": {"fast": 100, "short": 65, "medium": 20, "long": 0},
    "within_30_days": {"fast": 95, "short": 100, "medium": 50, "long": 10},
    "within_3_months": {"fast": 85, "short": 95, "medium": 100, "long": 50},
    "over_3_months": {"fast": 70, "short": 85, "medium": 95, "long": 100},
}

LEVEL_SCORE = {"low": 40.0, "medium": 70.0, "high": 100.0}
RECUR_SCORE = {"low": 35.0, "medium": 65.0, "high": 100.0}
SCALE_SCORE = {"low": 35.0, "medium": 65.0, "high": 100.0}
AI_SCORE = {"assistive": 50.0, "strong": 80.0, "core": 100.0}
ACQUISITION_BASE = {"low": 80.0, "medium": 60.0, "high": 40.0}
MARKET_SCORE = {
    ("current_growth", "A"): 100.0,
    ("durable_workflow", "B"): 75.0,
    ("distribution_dependent", "C"): 45.0,
}

WEIGHTS = {
    "capability_fit": 25.0,
    "revenue_timing_fit": 20.0,
    "acquisition_reachability": 15.0,
    "execution_fit": 15.0,
    "market_evidence": 10.0,
    "margin_profile": 5.0,
    "recurring_revenue": 5.0,
    "scalability": 3.0,
    "ai_leverage": 2.0,
}


@dataclass(frozen=True)
class CapabilityEvidence:
    state: str
    evidence: str

    def __post_init__(self) -> None:
        if self.state not in CAPABILITY_VALUES:
            raise ValueError(f"Unknown capability state: {self.state}")


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    revenue_urgency: str
    available_hours_weekly: float
    schedule_consistency: str
    starting_budget_thb: int
    maximum_loss_tolerance_thb: int
    devices: frozenset[str]
    capabilities: Mapping[str, CapabilityEvidence]
    preferred_work_modes: frozenset[str]
    customer_interaction_tolerance: str
    camera_tolerance: bool
    voice_tolerance: bool
    distribution_assets: frozenset[str] = frozenset()
    model_preferences: frozenset[str] = frozenset()
    skill_confidence: str = "medium"
    diagnostic_mode: str = "standard"
    constraints: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.revenue_urgency not in TIMING_FIT:
            raise ValueError(f"Unknown revenue urgency: {self.revenue_urgency}")
        if self.schedule_consistency not in {"low", "medium", "high"}:
            raise ValueError("schedule_consistency must be low/medium/high")
        if self.customer_interaction_tolerance not in {"low", "medium", "high"}:
            raise ValueError("customer_interaction_tolerance must be low/medium/high")
        if self.skill_confidence not in {"low", "medium", "high"}:
            raise ValueError("skill_confidence must be low/medium/high")


@dataclass(frozen=True)
class Opportunity:
    id: str
    name: str
    model_type: str
    buyer: str
    core_deliverable: str
    startup_cost_band: str
    time_to_first_revenue: str
    required_capabilities: Tuple[str, ...]
    minimum_device: str
    customer_interaction: str
    public_presence: str
    acquisition_modes: Tuple[str, ...]
    acquisition_difficulty: str
    margin_profile: str
    recurring_revenue_potential: str
    scalability: str
    ai_leverage: str
    market_demand_signal: str
    evidence_level: str
    hard_disqualifiers: Tuple[str, ...]
    cheap_validation_experiment: str
    work_modes: Tuple[str, ...] = ()
    hard_rule_tags: Tuple[str, ...] = ()


@dataclass
class OpportunityEvaluation:
    opportunity_id: str
    opportunity_name: str
    state: str
    fit_score: Optional[float]
    capability_average: float
    component_scores: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    demotions: List[str] = field(default_factory=list)


@dataclass
class RecommendationResult:
    decision_state: str
    primary_opportunity: Optional[str]
    fit_score: Optional[float]
    recommendation_confidence: str
    why_it_fits: List[str]
    constraints_checked: List[str]
    assumptions: List[str]
    alternatives: List[Dict[str, object]]
    rejected_or_demoted: List[Dict[str, object]]
    first_validation_experiment: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _op(
    id: str,
    name: str,
    model_type: str,
    startup: str,
    timing: str,
    caps: Sequence[str],
    device: str,
    interaction: str,
    public: str,
    acquisition: Sequence[str],
    acquisition_difficulty: str,
    margin: str,
    recurring: str,
    scalability: str,
    ai: str,
    demand: str,
    evidence: str,
    experiment: str,
    *,
    buyer: str = "controlled P2 buyer segment",
    deliverable: str = "controlled P2 deliverable",
    disqualifiers: Sequence[str] = (),
    work_modes: Sequence[str] = (),
    hard_rule_tags: Sequence[str] = (),
) -> Opportunity:
    return Opportunity(
        id=id,
        name=name,
        model_type=model_type,
        buyer=buyer,
        core_deliverable=deliverable,
        startup_cost_band=startup,
        time_to_first_revenue=timing,
        required_capabilities=tuple(caps),
        minimum_device=device,
        customer_interaction=interaction,
        public_presence=public,
        acquisition_modes=tuple(acquisition),
        acquisition_difficulty=acquisition_difficulty,
        margin_profile=margin,
        recurring_revenue_potential=recurring,
        scalability=scalability,
        ai_leverage=ai,
        market_demand_signal=demand,
        evidence_level=evidence,
        hard_disqualifiers=tuple(disqualifiers),
        cheap_validation_experiment=experiment,
        work_modes=tuple(work_modes),
        hard_rule_tags=tuple(hard_rule_tags),
    )


OPPORTUNITIES: Tuple[Opportunity, ...] = (
    _op("O01", "Spreadsheet Data Cleanup", "service", "zero", "fast",
        ("spreadsheet", "attention_detail", "data_reasoning"), "computer_required", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "professional_network"), "medium", "high", "medium", "medium", "strong", "current_growth", "A",
        "Create one synthetic before/after cleanup sample and offer a fixed-scope cleanup to 10–20 prospects.",
        disqualifiers=("phone-only for non-trivial files", "no practical spreadsheet evidence until skill verification"),
        work_modes=("organizing_data", "structured_problem_solving")),
    _op("O02", "PDF / Document to Spreadsheet Conversion", "service", "zero", "fast",
        ("attention_detail", "spreadsheet", "document_handling"), "computer_preferred", "low", "none",
        ("direct_outreach", "freelance_marketplace", "professional_network"), "medium", "high", "low", "medium", "strong", "current_growth", "A",
        "Build a 3-page sample conversion showing source document versus validated spreadsheet output.",
        disqualifiers=("unwillingness to perform manual QA",), work_modes=("organizing_data", "repetitive_operations"), hard_rule_tags=("manual_qa",)),
    _op("O03", "Dashboard & Business Reporting", "service", "very_low", "short",
        ("data_reasoning", "dashboard", "stakeholder_clarification"), "computer_required", "medium", "none",
        ("direct_outreach", "professional_network", "freelance_marketplace", "referrals"), "medium", "high", "high", "medium", "strong", "durable_workflow", "B",
        "Create one niche demo dashboard from public/synthetic data and ask 10 target businesses whether the KPIs support real weekly decisions.",
        disqualifiers=("no evidence of data/reporting capability",), work_modes=("organizing_data", "structured_problem_solving")),
    _op("O04", "Virtual Admin / Operations Assistant", "service", "zero", "short",
        ("reliability", "organization", "written_communication"), "computer_preferred", "high", "none",
        ("direct_outreach", "freelance_marketplace", "professional_network", "referrals"), "medium", "medium", "high", "medium", "assistive", "durable_workflow", "B",
        "Offer a one-week fixed-scope admin cleanup/follow-up package to a small business or professional contact.",
        disqualifiers=("extremely low customer-interaction tolerance", "highly inconsistent availability for response-sensitive work"),
        work_modes=("operations", "organizing_data", "support"), hard_rule_tags=("stable_response_window",)),
    _op("O05", "Customer Support / Inbox Management", "service", "zero", "short",
        ("communication", "patience", "process_discipline"), "phone_ok", "high", "none",
        ("direct_outreach", "ecommerce_community", "freelance_marketplace", "referrals"), "medium", "medium", "high", "medium", "assistive", "durable_workflow", "B",
        "Build a sample FAQ + response workflow for one business category and pitch a limited inbox-coverage trial.",
        disqualifiers=("low interaction tolerance", "inability to maintain agreed response windows"),
        work_modes=("support", "operations", "repetitive_operations"), hard_rule_tags=("stable_response_window",)),
    _op("O06", "Lead Research / Prospect List Building", "service", "zero", "short",
        ("research", "structured_data", "qualification_judgment"), "computer_required", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "agency_partnership", "professional_network"), "medium", "high", "medium", "medium", "strong", "durable_workflow", "B",
        "Produce 20 sample prospects for one narrow buyer profile and ask a seller to rate relevance.",
        disqualifiers=("weak research discipline", "no computer for larger research tasks"), work_modes=("research", "organizing_data")),
    _op("O07", "Outreach / Appointment Setting Support", "service", "zero", "short",
        ("customer_interaction", "sales_resilience", "communication"), "phone_ok", "high", "voice_optional",
        ("direct_outreach", "freelance_marketplace", "agency_partnership", "professional_network"), "high", "high", "high", "medium", "assistive", "durable_workflow", "B",
        "Run a 20-prospect manual outreach test for one clear offer and record reply rate, interest and objections.",
        disqualifiers=("low sales/customer-contact tolerance",), work_modes=("selling", "speaking", "support")),
    _op("O08", "Presentation & Document Formatting", "service", "zero", "short",
        ("visual_organization", "document_tools", "attention_detail"), "computer_preferred", "medium", "none",
        ("freelance_marketplace", "education_community", "professional_network", "direct_outreach"), "medium", "high", "medium", "medium", "strong", "current_growth", "A",
        "Publish three before/after examples from synthetic documents/slides.",
        disqualifiers=("no evidence of document/presentation capability for higher-complexity work",), work_modes=("visual_design", "writing", "structured_tasks")),
    _op("O09", "Translation / Localization", "service", "zero", "short",
        ("language_proficiency", "nuance", "qa"), "computer_preferred", "medium", "none",
        ("freelance_marketplace", "direct_outreach", "professional_network", "creator_community"), "medium", "high", "medium", "medium", "assistive", "current_growth", "A",
        "Create a side-by-side localization sample for one product page or short-video script.",
        disqualifiers=("weak target-language proficiency", "raw machine translation without human review"), work_modes=("writing", "language"), hard_rule_tags=("strong_language",)),
    _op("O10", "Short-form Video Editing", "service", "very_low", "short",
        ("video_editing", "storytelling_pacing", "visual_qa"), "production_capable_device", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "creator_community", "agency_partnership"), "medium", "high", "high", "medium", "strong", "current_growth", "A",
        "Edit three samples from licensed/self-created footage and pitch a fixed five-video starter pack.",
        disqualifiers=("device incapable of required editing workload",), work_modes=("visual_design", "video_production")),
    _op("O11", "AI UGC / Ad Creative Production", "service", "low", "short",
        ("ad_judgment", "storytelling_pacing", "ai_video", "brand_safety_qa"), "production_capable_device", "medium", "camera_optional",
        ("direct_outreach", "freelance_marketplace", "agency_partnership", "ecommerce_community"), "high", "medium", "high", "medium", "core", "current_growth", "A",
        "Create two spec ads for a fictional or owned product and ask 5–10 marketers/sellers which hook they would test.",
        disqualifiers=("inability to review claims/brand safety", "insufficient production-tool access"), work_modes=("visual_design", "video_production", "writing"), hard_rule_tags=("claim_review",)),
    _op("O12", "Social Media Content Pack", "productized_service", "very_low", "short",
        ("content_planning", "visual_copy_judgment", "client_communication"), "computer_preferred", "medium", "none",
        ("direct_outreach", "local_business_network", "professional_network", "referrals"), "medium", "high", "high", "medium", "strong", "durable_workflow", "B",
        "Make a seven-day sample pack for one niche and offer it to 10 businesses in that niche.",
        disqualifiers=("inability to maintain a consistent delivery cadence",), work_modes=("writing", "visual_design", "content"), hard_rule_tags=("consistent_delivery",)),
    _op("O13", "Canva Social Design", "service", "very_low", "short",
        ("visual_design", "canva"), "production_capable_device", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "local_business_network", "creator_community"), "medium", "high", "high", "medium", "strong", "current_growth", "A",
        "Create one six-post visual set for a sample brand and seek feedback/orders from a defined niche.",
        disqualifiers=("tool exposure without evidence must not qualify advanced design work",), work_modes=("visual_design",)),
    _op("O14", "YouTube Thumbnail Design", "service", "very_low", "short",
        ("visual_composition", "image_editing", "packaging_judgment"), "production_capable_device", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "creator_community", "agency_partnership"), "medium", "high", "high", "medium", "strong", "current_growth", "A",
        "Redesign three public thumbnails as non-commercial portfolio exercises and contact 10 channels with one tailored sample.",
        disqualifiers=("no portfolio/evidence of visual capability",), work_modes=("visual_design",)),
    _op("O15", "E-commerce Listing Optimization", "service", "very_low", "short",
        ("copy_research", "product_understanding", "platform_familiarity"), "computer_preferred", "medium", "none",
        ("direct_outreach", "ecommerce_community", "freelance_marketplace", "professional_network"), "medium", "high", "high", "medium", "strong", "durable_workflow", "B",
        "Rewrite one weak listing into a before/after sample and ask sellers to evaluate clarity and conversion relevance.",
        disqualifiers=("no relevant platform access", "inability to evaluate product claims accurately"), work_modes=("writing", "research", "operations"), hard_rule_tags=("platform_access", "claim_review")),
    _op("O16", "Marketplace Store Operations Support", "service", "zero", "short",
        ("operational_discipline", "platform_familiarity", "customer_communication"), "computer_preferred", "high", "none",
        ("direct_outreach", "ecommerce_community", "professional_network", "referrals"), "medium", "medium", "high", "medium", "assistive", "durable_workflow", "B",
        "Offer one fixed catalog-cleanup or listing-maintenance session instead of a vague VA package.",
        disqualifiers=("inability to maintain agreed response/service windows",), work_modes=("operations", "support", "selling"), hard_rule_tags=("stable_response_window", "platform_access")),
    _op("O17", "AI Product Visual / Image Editing", "service", "very_low", "short",
        ("image_judgment", "image_editing", "qa"), "production_capable_device", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "ecommerce_community", "owned_audience"), "medium", "medium", "medium", "medium", "core", "current_growth", "A",
        "Create three before/after examples using owned or permitted product images and pitch a five-image starter pack.",
        disqualifiers=("inability to avoid misleading product representation",), work_modes=("visual_design",), hard_rule_tags=("claim_review",)),
    _op("O18", "Content Repurposing", "productized_service", "very_low", "short",
        ("summarization", "editing", "content_judgment", "source_fidelity"), "computer_preferred", "medium", "none",
        ("direct_outreach", "freelance_marketplace", "creator_community", "referrals"), "medium", "high", "high", "medium", "strong", "durable_workflow", "B",
        "Take one public/owned long-form source and produce a clearly attributed multi-format sample pack.",
        disqualifiers=("weak source fidelity/QA",), work_modes=("writing", "content", "editing")),
    _op("O19", "AI Workflow Automation", "service", "low", "medium",
        ("process_mapping", "automation", "debugging", "security"), "computer_required", "high", "none",
        ("direct_outreach", "professional_network", "agency_partnership", "freelance_marketplace", "referrals"), "high", "high", "high", "medium", "core", "current_growth", "A",
        "Build one narrow demo such as lead form -> sheet -> notification using test data and show failure handling.",
        disqualifiers=("no technical implementation evidence", "inability to handle secrets/data safely"), work_modes=("technical", "structured_problem_solving"), hard_rule_tags=("safe_secrets",)),
    _op("O20", "Chatbot / FAQ Bot Setup", "service", "low", "medium",
        ("content_structuring", "integration", "testing", "fallback_design"), "computer_required", "high", "none",
        ("direct_outreach", "professional_network", "agency_partnership", "freelance_marketplace"), "high", "high", "high", "medium", "core", "current_growth", "A",
        "Build a demo against a synthetic FAQ set with a documented fallback when information is missing.",
        disqualifiers=("no capability to validate incorrect answers or escalation behavior",), work_modes=("technical", "content")),
    _op("O21", "Landing Page / No-code Site Setup", "service", "low", "medium",
        ("layout", "copy_structure", "web_tools"), "computer_required", "high", "none",
        ("direct_outreach", "freelance_marketplace", "local_business_network", "professional_network", "referrals"), "medium", "high", "medium", "medium", "strong", "durable_workflow", "B",
        "Build one sample landing page for a fictional niche and ask target buyers whether it contains enough information to contact/buy.",
        disqualifiers=("no web/no-code capability evidence for live client work",), work_modes=("technical", "visual_design", "writing")),
    _op("O22", "AI App / Prototype Implementation", "service", "moderate", "medium",
        ("software_development", "testing", "api_data", "deployment"), "computer_required", "high", "none",
        ("direct_outreach", "freelance_marketplace", "professional_network", "agency_partnership", "referrals"), "high", "high", "medium", "medium", "core", "current_growth", "A",
        "Ship one narrow demo with a real end-to-end workflow and public code/sample documentation.",
        disqualifiers=("no coding/product implementation evidence",), work_modes=("technical", "structured_problem_solving")),
    _op("O23", "Data Annotation / Labeling", "platform_work", "zero", "short",
        ("consistency", "instruction_following", "qa", "attention_detail"), "computer_preferred", "low", "none",
        ("platform_marketplace", "freelance_marketplace", "professional_network"), "medium", "low", "low", "low", "assistive", "current_growth", "A",
        "Complete a small benchmark labeling set and measure agreement/error rate before seeking paid work.",
        disqualifiers=("low attention to repetitive detail", "inability to follow labeling specifications consistently"), work_modes=("repetitive_operations", "structured_tasks")),
    _op("O24", "Tutoring / Explainer Service", "service", "zero", "short",
        ("subject_knowledge", "explanation", "customer_interaction"), "phone_ok", "high", "voice_optional",
        ("education_community", "professional_network", "local_business_network", "platform_marketplace", "referrals"), "medium", "high", "high", "low", "assistive", "durable_workflow", "B",
        "Offer one 30-minute diagnostic/tutorial session to a narrow audience and measure a defined learning outcome.",
        disqualifiers=("no evidence of subject capability", "very low interaction tolerance"), work_modes=("teaching", "speaking", "support")),
    _op("O25", "Digital Templates", "product", "very_low", "long",
        ("workflow_design", "packaging", "distribution"), "production_capable_device", "low", "none",
        ("platform_marketplace", "direct_outreach", "owned_audience", "algorithmic_distribution"), "high", "high", "medium", "high", "strong", "distribution_dependent", "C",
        "Publish one narrowly useful template and test 20 direct prospects or one marketplace before building a large catalog.",
        disqualifiers=("urgent first-income requirement with no existing audience/distribution",), work_modes=("visual_design", "product_building"), hard_rule_tags=("distribution_for_urgent",)),
    _op("O26", "Niche Digital Asset Packs", "product", "very_low", "long",
        ("production_quality", "niche_relevance", "packaging", "distribution"), "production_capable_device", "low", "none",
        ("platform_marketplace", "creator_community", "owned_audience", "algorithmic_distribution"), "high", "high", "medium", "high", "strong", "distribution_dependent", "C",
        "Create a five-item mini-pack and test direct interest before producing a large collection.",
        disqualifiers=("urgent income requirement with no distribution",), work_modes=("visual_design", "product_building"), hard_rule_tags=("distribution_for_urgent",)),
    _op("O27", "Affiliate Content", "content_commission", "low", "long",
        ("distribution", "product_selection", "content_consistency"), "phone_ok", "low", "camera_optional",
        ("owned_audience", "algorithmic_distribution", "creator_community"), "high", "medium", "medium", "high", "strong", "distribution_dependent", "C",
        "Choose one product/problem niche, publish a small controlled content set and measure impressions -> clicks -> qualified actions before scaling.",
        disqualifiers=("urgent predictable-income need", "no distribution plus low content tolerance", "belief that posting guarantees commissions"), work_modes=("content", "selling"), hard_rule_tags=("distribution_for_urgent",)),
    _op("O28", "Faceless YouTube Channel", "content_media_asset", "moderate", "long",
        ("research", "scripting", "production", "packaging", "persistence"), "production_capable_device", "low", "none",
        ("algorithmic_distribution", "owned_audience", "creator_community"), "high", "medium", "medium", "high", "strong", "distribution_dependent", "C",
        "Produce 3–5 videos in one narrow format and measure retention/click-through signals before committing to a large production system.",
        disqualifiers=("urgent income need", "very low weekly time", "expectation of immediate passive income"), work_modes=("content", "research", "video_production"), hard_rule_tags=("distribution_for_urgent", "time_intensive")),
)


OPPORTUNITY_BY_ID: Dict[str, Opportunity] = {op.id: op for op in OPPORTUNITIES}


class RecommendationEngine:
    """Deterministic P4 prototype implementing the P3 contract.

    No LLM calls, network access, persistence, or dynamic opportunity generation.
    """

    def __init__(self, opportunities: Iterable[Opportunity] = OPPORTUNITIES) -> None:
        self.opportunities = tuple(opportunities)
        ids = [op.id for op in self.opportunities]
        if len(ids) != len(set(ids)):
            raise ValueError("Opportunity IDs must be unique")

    def recommend(self, user: UserProfile) -> RecommendationResult:
        evaluations = [self.evaluate_opportunity(user, op) for op in self.opportunities]

        if user.diagnostic_mode == "skill_discovery":
            evidence_capability_max = max((e.capability_average for e in evaluations), default=0)
            if evidence_capability_max < 50:
                return self._no_match_result(
                    "DISCOVERY_REQUIRED",
                    evaluations,
                    "P1 is in skill_discovery mode and no opportunity has capability evidence strong enough to rank safely.",
                )

        primary = [e for e in evaluations if e.state == "ELIGIBLE_PRIMARY" and e.fit_score is not None]
        primary.sort(key=lambda e: (-float(e.fit_score), e.opportunity_id))

        if not primary or float(primary[0].fit_score or 0) < 65:
            return self._no_match_result(
                "NO_CONFIDENT_MATCH",
                evaluations,
                "No eligible primary opportunity reaches the minimum fit threshold with sufficient evidence.",
            )

        top = primary[0]
        second = primary[1] if len(primary) > 1 else None
        gap = float(top.fit_score or 0) - float(second.fit_score or 0) if second else 100.0

        if second and float(second.fit_score or 0) >= 65 and gap < 5:
            decision_state = "TWO_WAY_TEST"
            confidence = "MEDIUM"
        else:
            decision_state = "RECOMMEND"
            confidence = self._confidence(top, gap)
            if confidence == "LOW":
                return self._no_match_result(
                    "NO_CONFIDENT_MATCH",
                    evaluations,
                    "The best fit remains low-confidence, so P3 forbids a forced recommendation.",
                )

        op = OPPORTUNITY_BY_ID[top.opportunity_id]
        alternatives = [
            {
                "opportunity_id": e.opportunity_id,
                "name": e.opportunity_name,
                "state": e.state,
                "fit_score": e.fit_score,
            }
            for e in primary[1:4]
        ]
        rejected = [
            {
                "opportunity_id": e.opportunity_id,
                "name": e.opportunity_name,
                "state": e.state,
                "reasons": e.reasons + e.demotions,
            }
            for e in evaluations
            if e.state in {"INELIGIBLE", "VERIFY_FIRST", "ELIGIBLE_SECONDARY"}
        ][:12]

        why = self._why_it_fits(user, op, top)
        assumptions = self._assumptions(user, op, top)
        return RecommendationResult(
            decision_state=decision_state,
            primary_opportunity=top.opportunity_id,
            fit_score=round(float(top.fit_score or 0), 2),
            recommendation_confidence=confidence,
            why_it_fits=why,
            constraints_checked=[
                "device",
                "budget",
                "customer_interaction",
                "public_presence",
                "capability_evidence",
                "revenue_timing",
                "distribution_dependency",
                "schedule_compatibility",
            ],
            assumptions=assumptions,
            alternatives=alternatives,
            rejected_or_demoted=rejected,
            first_validation_experiment=op.cheap_validation_experiment,
        )

    def evaluate_opportunity(self, user: UserProfile, op: Opportunity) -> OpportunityEvaluation:
        cap_avg, cap_states = self._capability_average(user, op)
        reasons: List[str] = []
        demotions: List[str] = []

        hard_failure = self._hard_eligibility_failure(user, op, cap_states)
        if hard_failure:
            return OpportunityEvaluation(op.id, op.name, "INELIGIBLE", None, cap_avg, reasons=[hard_failure])

        if cap_avg < 50:
            return OpportunityEvaluation(
                op.id,
                op.name,
                "VERIFY_FIRST",
                None,
                cap_avg,
                reasons=["Required capability evidence is mostly UNKNOWN or weak; verify capability before ranking."],
            )

        state = "ELIGIBLE_PRIMARY"
        if op.public_presence == "camera_preferred" and not user.camera_tolerance:
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Camera is preferred but the user refuses camera; only a non-camera variant is suitable.")

        if user.revenue_urgency in {"within_7_days", "within_30_days"} and op.time_to_first_revenue == "long":
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Long-horizon path cannot be primary for a user needing money within 30 days.")
        if user.revenue_urgency == "within_7_days" and op.time_to_first_revenue == "medium":
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Medium-horizon path cannot be primary for a seven-day income need.")

        if (
            op.market_demand_signal == "distribution_dependent"
            and user.revenue_urgency in {"within_7_days", "within_30_days"}
            and not self._has_distribution_overlap(user, op)
        ):
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Distribution-dependent path lacks proven distribution for an urgent user.")

        if op.customer_interaction == "high" and user.schedule_consistency == "low":
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Response-sensitive work is a poor primary fit for an inconsistent schedule.")

        scores = self._component_scores(user, op, cap_avg)
        fit_score = sum(scores[k] * WEIGHTS[k] / 100.0 for k in WEIGHTS)
        if fit_score < 55 and state == "ELIGIBLE_PRIMARY":
            state = "ELIGIBLE_SECONDARY"
            demotions.append("Fit score is below the P3 primary-candidate floor of 55.")

        return OpportunityEvaluation(
            opportunity_id=op.id,
            opportunity_name=op.name,
            state=state,
            fit_score=round(fit_score, 2),
            capability_average=cap_avg,
            component_scores={k: round(v, 2) for k, v in scores.items()},
            reasons=reasons,
            demotions=demotions,
        )

    def _hard_eligibility_failure(
        self,
        user: UserProfile,
        op: Opportunity,
        cap_states: Mapping[str, str],
    ) -> Optional[str]:
        if op.minimum_device == "computer_required" and not self._has_computer(user):
            return "Opportunity requires a computer but P1 shows no computer access."
        if op.minimum_device == "production_capable_device" and not self._has_production_device(user):
            return "Opportunity requires a production-capable device that P1 does not show."

        budget_available = min(user.starting_budget_thb, user.maximum_loss_tolerance_thb)
        if COST_MAX_THB[op.startup_cost_band] > budget_available:
            return f"Startup-cost band {op.startup_cost_band} exceeds the user's acceptable cash risk."

        if op.customer_interaction == "high" and user.customer_interaction_tolerance == "low":
            return "Opportunity requires high customer interaction but the user tolerance is low."

        if any(state == "CONTRADICTED" for state in cap_states.values()):
            return "P1 evidence directly contradicts at least one required capability."

        if "stable_response_window" in op.hard_rule_tags and "cannot_maintain_response_window" in user.constraints:
            return "P2 requires reliable response windows but P1 explicitly says they cannot be maintained."
        if "manual_qa" in op.hard_rule_tags and "unwilling_manual_qa" in user.constraints:
            return "P2 requires manual QA but P1 explicitly rejects that work."
        if "strong_language" in op.hard_rule_tags and "weak_target_language" in user.constraints:
            return "Professional translation is ineligible because target-language proficiency is weak."
        if "safe_secrets" in op.hard_rule_tags and "unsafe_secret_handling" in user.constraints:
            return "Technical automation is ineligible because safe credential handling is not established."
        if "claim_review" in op.hard_rule_tags and "cannot_review_claims" in user.constraints:
            return "Offer is ineligible because product/brand claim review cannot be performed safely."
        if "platform_access" in op.hard_rule_tags and "no_relevant_platform_access" in user.constraints:
            return "Offer requires platform access that P1 says is unavailable."
        if "time_intensive" in op.hard_rule_tags and user.available_hours_weekly < 4:
            return "P2 marks this path as time-intensive and P1 shows fewer than four hours per week."

        if op.customer_interaction == "high" and user.available_hours_weekly <= 3:
            return "High-interaction opportunity is incompatible with the user's extremely limited weekly availability."
        return None

    def _capability_average(self, user: UserProfile, op: Opportunity) -> Tuple[float, Dict[str, str]]:
        states: Dict[str, str] = {}
        values: List[float] = []
        for capability in op.required_capabilities:
            evidence = user.capabilities.get(capability)
            state = evidence.state if evidence else "UNKNOWN"
            states[capability] = state
            values.append(CAPABILITY_VALUES[state])
        average = sum(values) / len(values) if values else 25.0
        if user.skill_confidence == "low":
            average = min(average, 45.0)
        return round(average, 2), states

    def _component_scores(self, user: UserProfile, op: Opportunity, cap_avg: float) -> Dict[str, float]:
        acquisition = ACQUISITION_BASE[op.acquisition_difficulty] + self._acquisition_boost(user, op)
        acquisition = min(acquisition, 100.0)

        work_fit = 100.0 if set(op.work_modes) & set(user.preferred_work_modes) else 60.0
        interaction_fit = self._interaction_fit(user.customer_interaction_tolerance, op.customer_interaction)
        public_fit = self._public_fit(user, op)
        model_fit = self._model_fit(user, op)

        if op.minimum_device == "computer_preferred" and not self._has_computer(user):
            model_fit = min(model_fit, 50.0)
        if op.customer_interaction == "high" and user.schedule_consistency == "medium":
            model_fit = min(model_fit, 75.0)
        if op.customer_interaction == "high" and user.schedule_consistency == "low":
            model_fit = min(model_fit, 35.0)

        execution = (work_fit + interaction_fit + public_fit + model_fit) / 4.0
        market = MARKET_SCORE.get((op.market_demand_signal, op.evidence_level), 45.0)

        return {
            "capability_fit": cap_avg,
            "revenue_timing_fit": float(TIMING_FIT[user.revenue_urgency][op.time_to_first_revenue]),
            "acquisition_reachability": acquisition,
            "execution_fit": execution,
            "market_evidence": market,
            "margin_profile": LEVEL_SCORE[op.margin_profile],
            "recurring_revenue": RECUR_SCORE[op.recurring_revenue_potential],
            "scalability": SCALE_SCORE[op.scalability],
            "ai_leverage": AI_SCORE[op.ai_leverage],
        }

    @staticmethod
    def _has_computer(user: UserProfile) -> bool:
        return bool({"windows", "mac", "linux", "computer"} & set(user.devices))

    @classmethod
    def _has_production_device(cls, user: UserProfile) -> bool:
        return cls._has_computer(user) or bool({"ipad", "tablet", "production_phone"} & set(user.devices))

    @staticmethod
    def _interaction_fit(user_level: str, required: str) -> float:
        order = {"low": 1, "medium": 2, "high": 3}
        if order[user_level] >= order[required]:
            return 100.0
        if user_level == "medium" and required == "high":
            return 75.0
        if user_level == "low" and required == "medium":
            return 35.0
        return 0.0

    @staticmethod
    def _public_fit(user: UserProfile, op: Opportunity) -> float:
        if op.public_presence == "none":
            return 100.0
        if op.public_presence == "voice_optional":
            return 100.0 if user.voice_tolerance else 75.0
        if op.public_presence == "camera_optional":
            return 100.0 if user.camera_tolerance else 75.0
        if op.public_presence == "camera_preferred":
            return 100.0 if user.camera_tolerance else 35.0
        return 60.0

    @staticmethod
    def _model_fit(user: UserProfile, op: Opportunity) -> float:
        if not user.model_preferences or "not_sure" in user.model_preferences:
            base = 60.0
        elif op.model_type in user.model_preferences:
            base = 100.0
        elif op.model_type == "productized_service" and "service" in user.model_preferences:
            base = 85.0
        else:
            base = 35.0

        if user.available_hours_weekly < 5 and op.model_type in {"content_media_asset", "content_commission"}:
            base = min(base, 35.0)
        return base

    def _acquisition_boost(self, user: UserProfile, op: Opportunity) -> float:
        overlap = set(user.distribution_assets) & set(op.acquisition_modes)
        if not overlap:
            return 0.0
        if overlap & {"owned_audience", "professional_network", "ecommerce_community", "education_community"}:
            return 20.0
        if overlap & {"local_business_network", "creator_community", "referrals", "agency_partnership"}:
            return 15.0
        if overlap & {"platform_marketplace", "freelance_marketplace", "direct_outreach"}:
            return 10.0
        return 0.0

    def _has_distribution_overlap(self, user: UserProfile, op: Opportunity) -> bool:
        return bool(set(user.distribution_assets) & set(op.acquisition_modes))

    @staticmethod
    def _confidence(top: OpportunityEvaluation, gap: float) -> str:
        evidence = top.component_scores.get("capability_fit", 0)
        market = top.component_scores.get("market_evidence", 0)
        acquisition = top.component_scores.get("acquisition_reachability", 0)
        score = float(top.fit_score or 0)
        if score >= 75 and evidence >= 65 and market >= 75 and acquisition >= 60 and gap >= 8:
            return "HIGH"
        if score >= 65 and evidence >= 50:
            return "MEDIUM"
        return "LOW"

    def _why_it_fits(self, user: UserProfile, op: Opportunity, top: OpportunityEvaluation) -> List[str]:
        proven = [
            cap for cap in op.required_capabilities
            if user.capabilities.get(cap) and user.capabilities[cap].state in {"PROVEN", "SIGNAL"}
        ]
        points = [
            f"Capability evidence supports {', '.join(proven[:3]) or 'the validation scope'}; capability fit is {top.component_scores.get('capability_fit', 0):.0f}/100.",
            f"P1 urgency is {user.revenue_urgency}; P2 timing band is {op.time_to_first_revenue}.",
            f"P2 startup cost is {op.startup_cost_band}; P1 acceptable cash risk is THB {min(user.starting_budget_thb, user.maximum_loss_tolerance_thb):,}.",
        ]
        overlap = set(user.distribution_assets) & set(op.acquisition_modes)
        if overlap:
            points.append(f"P1 already shows acquisition access overlapping P2 modes: {', '.join(sorted(overlap))}.")
        return points

    def _assumptions(self, user: UserProfile, op: Opportunity, top: OpportunityEvaluation) -> List[str]:
        assumptions: List[str] = []
        for cap in op.required_capabilities:
            state = user.capabilities.get(cap).state if user.capabilities.get(cap) else "UNKNOWN"
            if state == "SIGNAL":
                assumptions.append(f"{cap} is supported by a signal, not proven delivery evidence.")
            elif state == "UNKNOWN":
                assumptions.append(f"{cap} remains unknown and should be checked during the cheap experiment.")
        if top.component_scores.get("acquisition_reachability", 0) <= 60:
            assumptions.append("Customer acquisition is not yet proven; the validation experiment must test reachability before scaling.")
        return assumptions

    def _no_match_result(
        self,
        state: str,
        evaluations: Sequence[OpportunityEvaluation],
        reason: str,
    ) -> RecommendationResult:
        candidates = [e for e in evaluations if e.fit_score is not None]
        candidates.sort(key=lambda e: (-float(e.fit_score or 0), e.opportunity_id))
        return RecommendationResult(
            decision_state=state,
            primary_opportunity=None,
            fit_score=None,
            recommendation_confidence="LOW",
            why_it_fits=[reason],
            constraints_checked=[
                "device",
                "budget",
                "customer_interaction",
                "public_presence",
                "capability_evidence",
                "revenue_timing",
                "distribution_dependency",
                "schedule_compatibility",
            ],
            assumptions=[],
            alternatives=[
                {
                    "opportunity_id": e.opportunity_id,
                    "name": e.opportunity_name,
                    "state": e.state,
                    "fit_score": e.fit_score,
                }
                for e in candidates[:3]
            ],
            rejected_or_demoted=[
                {
                    "opportunity_id": e.opportunity_id,
                    "name": e.opportunity_name,
                    "state": e.state,
                    "reasons": e.reasons + e.demotions,
                }
                for e in evaluations
                if e.state in {"INELIGIBLE", "VERIFY_FIRST", "ELIGIBLE_SECONDARY"}
            ][:12],
            first_validation_experiment=None,
        )
