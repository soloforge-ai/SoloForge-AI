from __future__ import annotations

from backend.asset_forge.backend import content_strategy


def test_fallback_strategy_builds_three_selectable_plans(monkeypatch) -> None:
    monkeypatch.setattr(content_strategy, "_call_provider", lambda _: None)

    result = content_strategy.strategize_idea(
        "เขาบอกว่าใช้ AI ทำ Digital Product ขายได้ เราเลยลอง"
    )

    assert result["strategy"]["angle"] == "Build in Public / Experiment"
    assert result["strategy"]["recommended_plan_id"] == "mini_series"
    assert [plan["id"] for plan in result["plans"]] == [
        "quick_test",
        "mini_series",
        "seven_day",
    ]
    assert [plan["job_count"] for plan in result["plans"]] == [1, 3, 7]
    assert result["strategist_provider"] == "deterministic_fallback"


def test_seven_day_plan_keeps_future_results_as_dependency(monkeypatch) -> None:
    monkeypatch.setattr(content_strategy, "_call_provider", lambda _: None)

    result = content_strategy.strategize_idea(
        "เขาบอกว่าใช้ AI ทำ Digital Product ขายได้ เราเลยลอง"
    )
    plan = next(plan for plan in result["plans"] if plan["id"] == "seven_day")

    assert len(plan["jobs"]) == 7
    assert "performance_after_publish" in plan["jobs"][5]["depends_on"]
    assert "performance_after_publish" in plan["jobs"][6]["depends_on"]


def test_provider_shape_is_normalized_to_expected_plan_sizes(monkeypatch) -> None:
    raw = {
        "strategy": {
            "angle": "Test angle",
            "objective": "Test objective",
            "audience": "Test audience",
            "rationale": "Test rationale",
            "missing_inputs": ["product image"],
            "recommended_plan_id": "seven_day",
        },
        "plans": [
            {
                "id": "quick_test",
                "title": "One",
                "summary": "One",
                "job_count": 99,
                "goal": "reach",
                "platforms": ["tiktok"],
                "asset_requirements": [],
                "jobs": [{
                    "sequence": 1,
                    "title": "One",
                    "format": "short_video_demo",
                    "goal": "reach",
                    "hook_direction": "Hook",
                    "asset_requirements": [],
                    "depends_on": [],
                }],
            }
        ],
    }
    monkeypatch.setattr(
        content_strategy,
        "_call_provider",
        lambda _: (raw, "test_provider", "test_model"),
    )

    result = content_strategy.strategize_idea("ลองทำ Digital Product")

    assert result["strategist_provider"] == "test_provider"
    assert len(result["plans"]) == 3
    assert [len(plan["jobs"]) for plan in result["plans"]] == [1, 3, 7]
