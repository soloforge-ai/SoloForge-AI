from __future__ import annotations

from backend.asset_forge.backend.content_job_skill_adapter import (
    ContentJobSkillInputAdapter,
    preview_content_job_skill,
)


def _legacy_education_job() -> dict[str, object]:
    return {
        "id": "b2fe4c08-3710-45a4-8527-5f48c71d603d",
        "idea": (
            "AI Automation ต่างจากใช้ ChatGPT ธรรมดายังไง: "
            "จากเราเป็นคนสั่งทุกครั้ง ไปสู่ Trigger → AI → Rule → Action → Next step "
            "โดยมนุษย์อยู่ที่จุดตัดสินใจ"
        ),
        "status": "NEW",
        "publish_platform": "facebook",
        "hook": None,
        "cta": None,
        "caption": None,
        "content_package": {
            "goal": "education",
            "format": "carousel",
            "target_platforms": ["facebook", "tiktok"],
        },
    }


def test_adapter_maps_legacy_content_job_to_skill_input() -> None:
    adapted = ContentJobSkillInputAdapter.adapt(_legacy_education_job())

    assert adapted["job_id"] == "b2fe4c08-3710-45a4-8527-5f48c71d603d"
    assert adapted["goal"] == "education"
    assert adapted["platform"] == "facebook"
    assert adapted["ready_for_skill"] is True
    assert set(adapted["defaults_applied"]) == {"audience", "cta"}


def test_existing_queue_education_job_reaches_ready_for_approval() -> None:
    preview = preview_content_job_skill(_legacy_education_job())

    assert preview["status"] == "READY_FOR_APPROVAL"
    assert preview["skill_result"]["skill_id"] == "SHORT_EDUCATIONAL_V1"
    assert preview["skill_result"]["qa"]["result"] == "PASS"
    assert len(preview["skill_result"]["scenes"]) == 5
    assert preview["skill_result"]["asset_plan"]["generated_count"] == 0


def test_conversion_job_is_not_forced_into_educational_skill() -> None:
    row = {
        "id": "3501740c-04a4-415a-9abd-bfa43d086df4",
        "idea": "Facebook Affiliate Experiment: magnetic cable clip",
        "publish_platform": "facebook",
        "cta": "พิกัดอยู่ในคอมเมนต์",
        "content_package": {
            "goal": "conversion",
            "format": "short_video_demo",
        },
    }

    preview = preview_content_job_skill(row)

    assert preview["status"] == "DRAFT"
    assert preview["skill_result"]["skill_id"] == "UNSUPPORTED"
    assert preview["skill_result"]["status"] == "UNSUPPORTED"
    assert "audience" in preview["skill_input"]["missing_required"]


def test_adapter_reports_missing_input_instead_of_inventing_unknown_goal() -> None:
    row = {
        "id": "legacy-unknown",
        "idea": "หัวข้อเก่าที่ยังไม่มี metadata",
        "publish_platform": "facebook",
        "content_package": {},
    }

    preview = preview_content_job_skill(row)

    assert preview["status"] == "NEEDS_INPUT"
    assert "goal" in preview["missing_required"]
    assert "audience" in preview["missing_required"]
    assert "cta" in preview["missing_required"]
