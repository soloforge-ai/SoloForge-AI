from __future__ import annotations

from backend.asset_forge.backend import content_intake


def test_recommender_prefers_video_for_demo_problem() -> None:
    result = content_intake.recommend_formats(
        "ลองใช้ AI ทำตัวละคร 5 รูปแล้วหน้าไม่เหมือนกัน ทำไมถึงเปลี่ยน"
    )

    assert result["recommended_format"] == "short_video_demo"
    assert result["options"][0]["recommended"] is True
    assert result["options"][0]["needs_video"] is True
    assert result["miniboss"]["score"] >= 0


def test_recommender_prefers_personal_post_for_experience() -> None:
    result = content_intake.recommend_formats(
        "เมื่อก่อนเราเคยทำงานทุกอย่างเอง ตอนนั้นรู้สึกว่าเสียเวลาเยอะมาก"
    )

    assert result["recommended_format"] == "personal_post"
    assert result["options"][0]["goal"] == "connection"


def test_recommender_always_returns_four_choices() -> None:
    result = content_intake.recommend_formats("อยากทำคอนเทนต์เกี่ยวกับ AI")

    assert len(result["options"]) == 4
    assert {item["id"] for item in result["options"]} == {
        "short_video_demo",
        "carousel",
        "personal_post",
        "question_post",
    }


def test_find_recommendation_rejects_unknown_format() -> None:
    try:
        content_intake.find_recommendation("AI idea", "podcast")
    except ValueError as exc:
        assert "Unknown recommendation format" in str(exc)
    else:
        raise AssertionError("unknown format should fail")
