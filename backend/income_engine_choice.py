from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from income_engine import (
    OPPORTUNITIES,
    OPPORTUNITY_BY_ID,
    Opportunity,
    OpportunityEvaluation,
    RecommendationEngine,
    UserProfile,
)


class PreferenceTradeoffEngine:
    """P4 calibration layer that preserves user preference without hiding tradeoffs.

    The base RecommendationEngine remains the deterministic source for eligibility,
    scoring, confidence, and no-match behavior. This layer only changes the final
    decision presentation when an explicit business-model preference conflicts
    with a stronger practical/revenue-timing path.

    It never guarantees income and never overrides hard eligibility.
    """

    def __init__(
        self,
        base_engine: Optional[RecommendationEngine] = None,
        opportunities: Iterable[Opportunity] = OPPORTUNITIES,
    ) -> None:
        self.base_engine = base_engine or RecommendationEngine(opportunities)
        self.opportunities = tuple(opportunities)

    def recommend(self, user: UserProfile) -> Dict[str, object]:
        base = self.base_engine.recommend(user)
        payload = base.to_dict()
        payload["tradeoff_options"] = []
        payload["tradeoff_summary"] = []
        payload["decision_policy"] = "preference_first_tradeoff_visible_user_decides"

        if base.decision_state not in {"RECOMMEND", "TWO_WAY_TEST"}:
            return payload

        explicit_preferences = self._explicit_preferences(user)
        if not explicit_preferences:
            return payload

        evaluations = [
            self.base_engine.evaluate_opportunity(user, opportunity)
            for opportunity in self.opportunities
        ]
        eligible = [
            evaluation
            for evaluation in evaluations
            if evaluation.state == "ELIGIBLE_PRIMARY"
            and evaluation.fit_score is not None
            and float(evaluation.fit_score) >= 55
        ]
        eligible.sort(key=lambda item: (-float(item.fit_score or 0), item.opportunity_id))
        if not eligible:
            return payload

        preferred = [
            evaluation
            for evaluation in eligible
            if self._matches_model_preference(
                explicit_preferences,
                OPPORTUNITY_BY_ID[evaluation.opportunity_id],
            )
        ]
        if not preferred:
            payload["tradeoff_summary"] = [
                "The user's stated business-model preference currently has no eligible path with enough evidence to offer safely."
            ]
            return payload

        preference_choice = preferred[0]
        practical_choice = eligible[0]

        if preference_choice.opportunity_id == practical_choice.opportunity_id:
            return payload

        preference_opportunity = OPPORTUNITY_BY_ID[preference_choice.opportunity_id]
        practical_opportunity = OPPORTUNITY_BY_ID[practical_choice.opportunity_id]

        # Only raise a user decision when the practical path has a visible economic
        # advantage. Otherwise preference already deserves precedence.
        if not self._has_revenue_advantage(practical_choice, preference_choice):
            payload["primary_opportunity"] = preference_choice.opportunity_id
            payload["fit_score"] = round(float(preference_choice.fit_score or 0), 2)
            payload["why_it_fits"] = [
                "The user's explicit business-model preference is eligible and there is no clear structural revenue advantage strong enough to justify steering away from it."
            ]
            return payload

        payload["decision_state"] = "TRADEOFF_CHOICE"
        payload["primary_opportunity"] = None
        payload["fit_score"] = None
        payload["recommendation_confidence"] = "MEDIUM"
        payload["why_it_fits"] = [
            "The path the user wants and the path with the stronger practical/revenue structure are different, so SoloForge does not choose on the user's behalf."
        ]
        payload["first_validation_experiment"] = None
        payload["tradeoff_options"] = [
            self._option_payload(
                role="PREFERENCE_PATH",
                evaluation=preference_choice,
                opportunity=preference_opportunity,
                user=user,
            ),
            self._option_payload(
                role="REVENUE_PRIORITY_PATH",
                evaluation=practical_choice,
                opportunity=practical_opportunity,
                user=user,
            ),
        ]
        payload["tradeoff_summary"] = self._build_tradeoff_summary(
            preference_choice,
            preference_opportunity,
            practical_choice,
            practical_opportunity,
        )
        return payload

    @staticmethod
    def _explicit_preferences(user: UserProfile) -> frozenset[str]:
        return frozenset(
            preference
            for preference in user.model_preferences
            if preference and preference != "not_sure"
        )

    @staticmethod
    def _matches_model_preference(
        preferences: frozenset[str],
        opportunity: Opportunity,
    ) -> bool:
        if opportunity.model_type in preferences:
            return True
        if "service" in preferences and opportunity.model_type == "productized_service":
            return True
        return False

    @staticmethod
    def _has_revenue_advantage(
        practical: OpportunityEvaluation,
        preferred: OpportunityEvaluation,
    ) -> bool:
        practical_scores = practical.component_scores
        preferred_scores = preferred.component_scores
        return any(
            practical_scores.get(component, 0) > preferred_scores.get(component, 0) + margin
            for component, margin in (
                ("revenue_timing_fit", 10),
                ("acquisition_reachability", 10),
                ("market_evidence", 20),
            )
        )

    @staticmethod
    def _option_payload(
        role: str,
        evaluation: OpportunityEvaluation,
        opportunity: Opportunity,
        user: UserProfile,
    ) -> Dict[str, object]:
        scores = evaluation.component_scores
        return {
            "role": role,
            "opportunity_id": opportunity.id,
            "name": opportunity.name,
            "model_type": opportunity.model_type,
            "matches_user_preference": opportunity.model_type in user.model_preferences,
            "fit_score": evaluation.fit_score,
            "time_to_first_revenue": opportunity.time_to_first_revenue,
            "capability_fit": scores.get("capability_fit"),
            "revenue_timing_fit": scores.get("revenue_timing_fit"),
            "acquisition_reachability": scores.get("acquisition_reachability"),
            "execution_fit": scores.get("execution_fit"),
            "market_evidence": scores.get("market_evidence"),
            "first_validation_experiment": opportunity.cheap_validation_experiment,
        }

    @staticmethod
    def _build_tradeoff_summary(
        preferred: OpportunityEvaluation,
        preferred_opportunity: Opportunity,
        practical: OpportunityEvaluation,
        practical_opportunity: Opportunity,
    ) -> List[str]:
        preferred_scores = preferred.component_scores
        practical_scores = practical.component_scores
        summary: List[str] = [
            f"Preference path: {preferred_opportunity.name} matches the user's stated model preference.",
            f"Revenue-priority path: {practical_opportunity.name} has the stronger overall practical score despite the preference penalty.",
            (
                "Revenue timing differs: "
                f"{preferred_opportunity.time_to_first_revenue} vs {practical_opportunity.time_to_first_revenue}; "
                "these are structural timing bands, not income promises."
            ),
        ]

        if preferred_scores.get("execution_fit", 0) > practical_scores.get("execution_fit", 0):
            summary.append(
                "The preference path fits the user's desired way of working better, "
                f"with execution fit {preferred_scores.get('execution_fit', 0):.0f} vs {practical_scores.get('execution_fit', 0):.0f}."
            )
        if practical_scores.get("market_evidence", 0) > preferred_scores.get("market_evidence", 0):
            summary.append(
                "The revenue-priority path has stronger current market evidence, "
                f"{practical_scores.get('market_evidence', 0):.0f} vs {preferred_scores.get('market_evidence', 0):.0f}."
            )
        if practical_scores.get("acquisition_reachability", 0) > preferred_scores.get("acquisition_reachability", 0):
            summary.append(
                "The revenue-priority path is structurally easier to reach buyers for this user, "
                f"{practical_scores.get('acquisition_reachability', 0):.0f} vs {preferred_scores.get('acquisition_reachability', 0):.0f}."
            )

        summary.append(
            "SoloForge must show both paths and ask the user which objective matters more now: preferred work model or faster revenue validation."
        )
        return summary
