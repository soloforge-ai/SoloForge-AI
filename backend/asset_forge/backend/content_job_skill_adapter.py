"""Adapter from legacy/current content_jobs rows into Content Skill input.

This module is intentionally deterministic. It does not mutate the database,
call an LLM/provider, generate assets, or publish content.
"""

from __future__ import annotations

from typing import Any

from backend.content_skill_runtime import plan_content_job


_DEFAULT_AUDIENCE_BY_GOAL = {
    "education": "SoloForge audience interested in practical AI tools and automation",
    "educational": "SoloForge audience interested in practical AI tools and automation",
    "reach_education": "SoloForge audience interested in practical AI tools and automation",
    "engagement": "SoloForge social audience",
    "personal_brand": "SoloForge founder-journey audience",
}

_DEFAULT_CTA_BY_GOAL = {
    "education": "บันทึกโพสต์นี้ไว้ แล้วลองเอาไปใช้กับงานของคุณ",
    "educational": "บันทึกโพสต์นี้ไว้ แล้วลองเอาไปใช้กับงานของคุณ",
    "reach_education": "บันทึกโพสต์นี้ไว้ แล้วลองเอาไปใช้กับงานของคุณ",
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean(item) for item in value if _clean(item)]


class ContentJobSkillInputAdapter:
    """Translate a content_jobs row into the provider-agnostic Skill contract."""

    @classmethod
    def adapt(cls, row: dict[str, Any]) -> dict[str, Any]:
        package = row.get("content_package")
        package = dict(package) if isinstance(package, dict) else {}

        goal = _clean(package.get("goal") or row.get("goal")).lower()
        platform = _clean(row.get("publish_platform") or package.get("platform") or "short_form").lower()
        topic = _clean(row.get("idea") or package.get("topic"))
        hook = _clean(row.get("hook") or package.get("hook"))
        cta = _clean(row.get("cta") or package.get("cta"))
        audience = _clean(
            package.get("audience")
            or package.get("target_audience")
            or package.get("persona")
        )

        defaults_applied: list[str] = []
        if not audience and goal in _DEFAULT_AUDIENCE_BY_GOAL:
            audience = _DEFAULT_AUDIENCE_BY_GOAL[goal]
            defaults_applied.append("audience")

        if not cta and goal in _DEFAULT_CTA_BY_GOAL:
            cta = _DEFAULT_CTA_BY_GOAL[goal]
            defaults_applied.append("cta")

        source_facts = _list_of_strings(
            package.get("source_facts")
            or package.get("facts")
            or package.get("proof_points")
        )
        approved_assets = _list_of_strings(
            package.get("approved_assets")
            or package.get("asset_refs")
        )

        adapted: dict[str, Any] = {
            "job_id": _clean(row.get("id") or row.get("job_id")),
            "topic": topic,
            "audience": audience,
            "goal": goal,
            "cta": cta,
            "platform": platform,
            "source_facts": source_facts,
            "approved_assets": approved_assets,
            "requires_generated_asset": bool(package.get("requires_generated_asset", False)),
            "storyboard_approved": bool(package.get("storyboard_approved", False)),
            "defaults_applied": defaults_applied,
        }

        if hook:
            adapted["hook"] = hook
        if _clean(row.get("caption") or package.get("caption")):
            adapted["caption"] = _clean(row.get("caption") or package.get("caption"))
        if _clean(package.get("core_idea")):
            adapted["core_idea"] = _clean(package.get("core_idea"))
        if _clean(package.get("skill_id")):
            adapted["skill_id"] = _clean(package.get("skill_id"))

        missing = [
            field
            for field in ("topic", "audience", "goal", "cta")
            if not _clean(adapted.get(field))
        ]
        adapted["missing_required"] = missing
        adapted["ready_for_skill"] = not missing
        return adapted


def preview_content_job_skill(row: dict[str, Any]) -> dict[str, Any]:
    """Adapt and run one existing content job without changing persistent state."""
    skill_input = ContentJobSkillInputAdapter.adapt(row)
    if not skill_input["ready_for_skill"]:
        return {
            "job_id": skill_input["job_id"],
            "status": "NEEDS_INPUT",
            "missing_required": skill_input["missing_required"],
            "defaults_applied": skill_input["defaults_applied"],
            "skill_input": skill_input,
        }

    result = plan_content_job(skill_input)
    return {
        "job_id": skill_input["job_id"],
        "status": result.get("state") or result.get("status"),
        "defaults_applied": skill_input["defaults_applied"],
        "skill_input": skill_input,
        "skill_result": result,
    }
