"""Provider-agnostic Content Skill runtime for SoloForge MVP v0.1.

The runtime intentionally stops at READY_FOR_APPROVAL. It does not generate
expensive assets and does not publish content.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


DEFAULT_SKILL_ID = "SHORT_EDUCATIONAL_V1"
UNSUPPORTED = "UNSUPPORTED"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "content_skills"


class ContentSkillRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _DATA_DIR
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, skill_id: str) -> dict[str, Any]:
        normalized = skill_id.strip().upper()
        if normalized in self._cache:
            return deepcopy(self._cache[normalized])

        candidates = sorted(self.root.glob("*.skill.json"))
        for path in candidates:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if str(payload.get("skill_id") or "").strip().upper() == normalized:
                self._cache[normalized] = payload
                return deepcopy(payload)
        raise KeyError(f"Unknown content skill: {skill_id}")


class ContentSkillRouter:
    EDUCATIONAL_GOALS = {
        "education",
        "educational",
        "problem",
        "problem_aware",
        "proof",
        "proof_content",
    }
    SHORT_FORM_PLATFORMS = {
        "",
        "short_form",
        "tiktok",
        "instagram",
        "facebook",
        "youtube",
        "youtube_shorts",
    }

    @classmethod
    def select(cls, job: dict[str, Any]) -> str:
        explicit = str(job.get("skill_id") or "").strip().upper()
        if explicit:
            return explicit

        goal = str(job.get("goal") or "").strip().lower()
        platform = str(job.get("platform") or "short_form").strip().lower()
        duration = int(job.get("target_duration_sec") or 25)

        if (
            goal in cls.EDUCATIONAL_GOALS
            and platform in cls.SHORT_FORM_PLATFORMS
            and duration <= 35
        ):
            return DEFAULT_SKILL_ID
        return UNSUPPORTED


class ContentSkillPlanner:
    @staticmethod
    def _validate_required(job: dict[str, Any], skill: dict[str, Any]) -> None:
        required = list((skill.get("input_contract") or {}).get("required") or [])
        missing = [name for name in required if not str(job.get(name) or "").strip()]
        if missing:
            raise ValueError(
                "Missing required content-skill inputs: " + ", ".join(sorted(missing))
            )

    @staticmethod
    def _durations(scene_count: int, total: int) -> list[int]:
        base = {
            3: [3, 14, 5],
            4: [2, 7, 10, 5],
            5: [2, 5, 8, 5, 5],
        }[scene_count]
        base_total = sum(base)
        scaled = [max(1, round(value * total / base_total)) for value in base]
        delta = total - sum(scaled)
        scaled[-1] += delta
        return scaled

    @staticmethod
    def _scene_roles(skill: dict[str, Any], scene_count: int) -> list[str]:
        defaults = list(
            (skill.get("production_rules") or {}).get("default_scene_roles") or []
        )
        if scene_count == 5 and len(defaults) >= 5:
            return defaults[:5]
        if scene_count == 4:
            return ["HOOK", "PROBLEM", "EXPLANATION_OR_PROOF", "CTA"]
        return ["HOOK", "EXPLANATION_OR_PROOF", "CTA"]

    @staticmethod
    def _asset_for_scene(
        scene_no: int,
        approved_assets: list[str],
        *,
        requires_generated_asset: bool,
    ) -> tuple[str, bool]:
        if scene_no <= len(approved_assets):
            return approved_assets[scene_no - 1], False
        if requires_generated_asset:
            return "GENERATED_ASSET", True
        return "TEMPLATE", False

    @classmethod
    def plan(
        cls,
        job: dict[str, Any],
        skill: dict[str, Any],
    ) -> dict[str, Any]:
        cls._validate_required(job, skill)

        production = skill.get("production_rules") or {}
        scene_rules = production.get("scene_count") or {}
        defaults = (skill.get("input_contract") or {}).get("defaults") or {}
        scene_count = int(job.get("scene_count") or scene_rules.get("default") or 5)
        target_duration = int(
            job.get("target_duration_sec")
            or defaults.get("target_duration_sec")
            or 25
        )

        topic = str(job["topic"]).strip()
        audience = str(job["audience"]).strip()
        goal = str(job["goal"]).strip()
        cta = str(job["cta"]).strip()
        source_facts = [
            str(value).strip()
            for value in (job.get("source_facts") or [])
            if str(value).strip()
        ]
        approved_assets = [
            str(value).strip()
            for value in (job.get("approved_assets") or [])
            if str(value).strip()
        ]
        requires_generated_asset = bool(job.get("requires_generated_asset"))

        hook = str(job.get("hook") or "").strip()
        if not hook:
            hook = topic if topic.endswith(("?", "？")) else f"{topic} — รู้จุดนี้หรือยัง?"

        core_idea = str(job.get("core_idea") or "").strip()
        if not core_idea:
            core_idea = source_facts[0] if source_facts else topic

        roles = cls._scene_roles(skill, scene_count)
        durations = cls._durations(scene_count, target_duration)

        fact_cursor = 0
        scenes: list[dict[str, Any]] = []
        for index, role in enumerate(roles, start=1):
            if role == "HOOK":
                narration = hook
                on_screen_text = hook[:80]
                visual_direction = "Show the problem or contrast immediately."
            elif role == "PROBLEM":
                narration = f"ประเด็นคือ {topic}"
                on_screen_text = topic[:80]
                visual_direction = "Make the problem concrete and easy to recognize."
            elif role == "EXPLANATION_OR_PROOF":
                if source_facts:
                    narration = source_facts[min(fact_cursor, len(source_facts) - 1)]
                    fact_cursor += 1
                else:
                    narration = core_idea
                on_screen_text = core_idea[:80]
                visual_direction = "Explain or prove the single core idea."
            elif role == "RESULT":
                narration = source_facts[-1] if source_facts else core_idea
                on_screen_text = "ผลลัพธ์"
                visual_direction = "Show the expected result or useful takeaway."
            else:
                narration = cta
                on_screen_text = cta[:80]
                visual_direction = "Simple CTA card with one action."

            asset_source, generation_needed = cls._asset_for_scene(
                index,
                approved_assets,
                requires_generated_asset=requires_generated_asset,
            )
            scenes.append(
                {
                    "scene_no": index,
                    "role": role,
                    "duration_sec": durations[index - 1],
                    "narration": narration,
                    "on_screen_text": on_screen_text,
                    "visual_direction": visual_direction,
                    "asset_source": asset_source,
                    "generation_needed": generation_needed,
                }
            )

        generated_count = sum(1 for scene in scenes if scene["generation_needed"])
        reuse_count = sum(
            1
            for scene in scenes
            if scene["asset_source"] not in {"TEMPLATE", "GENERATED_ASSET"}
        )
        template_count = sum(
            1 for scene in scenes if scene["asset_source"] == "TEMPLATE"
        )

        return {
            "job_id": str(job.get("job_id") or ""),
            "skill_id": str(skill["skill_id"]),
            "skill_version": str(skill["version"]),
            "state": "STORYBOARD_READY",
            "topic": topic,
            "audience": audience,
            "goal": goal,
            "hook": hook,
            "script": {
                "core_idea": core_idea,
                "estimated_duration_sec": sum(durations),
            },
            "scenes": scenes,
            "asset_plan": {
                "reuse_count": reuse_count,
                "template_count": template_count,
                "generated_count": generated_count,
            },
            "caption": str(job.get("caption") or f"{topic} — {core_idea}").strip(),
            "cta": cta,
            "source_facts": source_facts,
            "character_lock": job.get("character_lock"),
            "storyboard_approved": bool(job.get("storyboard_approved")),
            "requires_source_facts": bool(job.get("requires_source_facts")),
            "character_lock_required": bool(job.get("character_lock_required")),
        }


class ContentSkillQA:
    @classmethod
    def validate(
        cls,
        plan: dict[str, Any],
        skill: dict[str, Any],
    ) -> dict[str, Any]:
        failures: list[dict[str, str]] = []

        def add(rule_id: str, severity: str, reason: str) -> None:
            failures.append(
                {"id": rule_id, "severity": severity, "reason": reason}
            )

        core_idea = str((plan.get("script") or {}).get("core_idea") or "").strip()
        if not core_idea:
            add("Q001", "BLOCK", "Exactly one core idea is required.")

        cta = str(plan.get("cta") or "").strip()
        if not cta:
            add("Q002", "BLOCK", "Exactly one CTA is required.")

        scenes = list(plan.get("scenes") or [])
        if not 3 <= len(scenes) <= 5:
            add("Q003", "BLOCK", "Scene count must be between 3 and 5.")

        total_duration = sum(int(scene.get("duration_sec") or 0) for scene in scenes)
        if total_duration > 35:
            add("Q004", "BLOCK", "Planned duration exceeds 35 seconds.")

        if plan.get("requires_source_facts") and not plan.get("source_facts"):
            add("Q006", "BLOCK", "Required source facts are missing.")

        if plan.get("character_lock_required") and not plan.get("character_lock"):
            add("Q007", "BLOCK", "Required Character Lock is missing.")

        if any(bool(scene.get("generation_needed")) for scene in scenes):
            if not plan.get("storyboard_approved"):
                add(
                    "Q009",
                    "BLOCK",
                    "Storyboard approval is required before expensive generation.",
                )

        if plan.get("asset_plan", {}).get("generated_count", 0) > 0 and plan.get(
            "asset_plan", {}
        ).get("reuse_count", 0) > 0:
            add(
                "Q005",
                "WARN",
                "Prefer approved/reusable assets before generated assets.",
            )

        block_ids = [item["id"] for item in failures if item["severity"] == "BLOCK"]
        warn_ids = [item["id"] for item in failures if item["severity"] == "WARN"]
        if block_ids:
            result = "REGENERATE"
        elif warn_ids:
            result = "MINOR_FIX"
        else:
            result = "PASS"

        return {
            "result": result,
            "failed_rules": [item["id"] for item in failures],
            "details": failures,
        }


class ApprovalPackageBuilder:
    @staticmethod
    def build(plan: dict[str, Any], qa: dict[str, Any]) -> dict[str, Any]:
        result = str(qa.get("result") or "REGENERATE")
        if result == "PASS":
            status = "READY_FOR_APPROVAL"
            decision = "APPROVE"
            recommended_action = "APPROVE"
            risk = "LOW"
        elif result == "MINOR_FIX":
            status = "NEEDS_REVISION"
            decision = "REVISE"
            recommended_action = "REVISE"
            risk = "MEDIUM"
        else:
            status = "BLOCKED"
            decision = "REVISE"
            recommended_action = "REVISE"
            risk = "HIGH"

        duration = int((plan.get("script") or {}).get("estimated_duration_sec") or 0)
        scenes = len(plan.get("scenes") or [])
        generated = int((plan.get("asset_plan") or {}).get("generated_count") or 0)
        summary = (
            f"{duration}s short, {scenes} scenes, {generated} new generated assets, "
            "one core idea, one CTA."
        )

        return {
            "job_id": str(plan.get("job_id") or ""),
            "skill_id": str(plan.get("skill_id") or ""),
            "status": status,
            "summary": summary,
            "decision_required": decision,
            "recommended_action": recommended_action,
            "risk": risk,
            "qa": {
                "result": result,
                "failed_rules": list(qa.get("failed_rules") or []),
            },
        }


def plan_content_job(
    job: dict[str, Any],
    *,
    registry: ContentSkillRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or ContentSkillRegistry()
    skill_id = ContentSkillRouter.select(job)
    if skill_id == UNSUPPORTED:
        return {
            "job_id": str(job.get("job_id") or ""),
            "skill_id": UNSUPPORTED,
            "state": "DRAFT",
            "status": "UNSUPPORTED",
            "reason": "No approved MVP skill matches this job. Manual selection is required.",
        }

    skill = registry.get(skill_id)
    plan = ContentSkillPlanner.plan(job, skill)
    qa = ContentSkillQA.validate(plan, skill)
    approval = ApprovalPackageBuilder.build(plan, qa)

    result = deepcopy(plan)
    result["qa"] = qa
    result["approval_package"] = approval
    result["state"] = approval["status"]
    return result
