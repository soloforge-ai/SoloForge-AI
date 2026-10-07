from __future__ import annotations

from pathlib import Path

from backend.asset_forge.backend.content_skill_runtime import (
    ApprovalPackageBuilder,
    ContentSkillPlanner,
    ContentSkillQA,
    ContentSkillRegistry,
    ContentSkillRouter,
    UNSUPPORTED,
    plan_content_job,
)


def _job(index: int = 1) -> dict[str, object]:
    return {
        "job_id": f"demo_{index:03d}",
        "topic": f"AI workflow lesson {index}",
        "audience": "AI creators",
        "goal": "education",
        "cta": "บันทึกโพสต์นี้ไว้",
        "platform": "short_form",
        "source_facts": [
            "Lock one stable variable before changing scene variables.",
            "Change one production variable at a time when testing.",
        ],
        "approved_assets": ["proof.png", "result.png"],
    }


def test_registry_loads_short_educational_skill() -> None:
    skill = ContentSkillRegistry().get("SHORT_EDUCATIONAL_V1")
    assert skill["skill_id"] == "SHORT_EDUCATIONAL_V1"
    assert skill["version"] == "0.1.0"
    assert skill["status"] == "ACTIVE"


def test_router_selects_only_supported_mvp_work() -> None:
    assert ContentSkillRouter.select(_job()) == "SHORT_EDUCATIONAL_V1"

    unsupported = _job()
    unsupported["goal"] = "sales"
    assert ContentSkillRouter.select(unsupported) == UNSUPPORTED


def test_planner_produces_structured_storyboard_without_expensive_generation() -> None:
    registry = ContentSkillRegistry()
    skill = registry.get("SHORT_EDUCATIONAL_V1")
    plan = ContentSkillPlanner.plan(_job(), skill)

    assert plan["state"] == "STORYBOARD_READY"
    assert 3 <= len(plan["scenes"]) <= 5
    assert plan["script"]["estimated_duration_sec"] <= 35
    assert plan["asset_plan"]["generated_count"] == 0
    assert all(
        scene["asset_source"] != "GENERATED_ASSET"
        for scene in plan["scenes"]
    )


def test_qa_blocks_duration_scene_and_generation_violations() -> None:
    registry = ContentSkillRegistry()
    skill = registry.get("SHORT_EDUCATIONAL_V1")
    plan = ContentSkillPlanner.plan(_job(), skill)

    plan["scenes"] = plan["scenes"] * 2
    for scene in plan["scenes"]:
        scene["duration_sec"] = 10
        scene["generation_needed"] = True

    qa = ContentSkillQA.validate(plan, skill)

    assert qa["result"] == "REGENERATE"
    assert "Q003" in qa["failed_rules"]
    assert "Q004" in qa["failed_rules"]
    assert "Q009" in qa["failed_rules"]


def test_approval_package_is_compact_and_machine_readable() -> None:
    result = plan_content_job(_job())

    approval = result["approval_package"]
    assert approval["status"] == "READY_FOR_APPROVAL"
    assert approval["decision_required"] == "APPROVE"
    assert approval["qa"]["result"] == "PASS"
    assert len(approval["summary"]) < 600


def test_same_skill_plans_five_distinct_jobs_without_workflow_rewrite() -> None:
    outputs = [plan_content_job(_job(index)) for index in range(1, 6)]

    assert {item["skill_id"] for item in outputs} == {"SHORT_EDUCATIONAL_V1"}
    assert all(item["approval_package"]["status"] == "READY_FOR_APPROVAL" for item in outputs)
    assert len({item["job_id"] for item in outputs}) == 5


def test_expensive_generation_cannot_begin_before_storyboard_approval() -> None:
    job = _job()
    job["requires_generated_asset"] = True

    result = plan_content_job(job)

    assert result["qa"]["result"] == "REGENERATE"
    assert "Q009" in result["qa"]["failed_rules"]
    assert result["approval_package"]["status"] == "BLOCKED"


def test_unsupported_job_requires_manual_selection() -> None:
    job = _job()
    job["goal"] = "conversion"

    result = plan_content_job(job)

    assert result["skill_id"] == "UNSUPPORTED"
    assert result["status"] == "UNSUPPORTED"
