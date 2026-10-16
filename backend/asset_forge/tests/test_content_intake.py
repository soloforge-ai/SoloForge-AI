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


def test_recommender_routes_affiliate_short_video_to_facebook_first() -> None:
    result = content_intake.recommend_formats(
        "รีวิวสินค้าที่ใช้จริง ก่อนใช้สายชาร์จตกใต้โต๊ะ หลังใช้คลิปแม่เหล็กดีขึ้น "
        "Shopee affiliate https://s.shopee.co.th/example"
    )

    video = next(
        item for item in result["options"] if item["id"] == "short_video_demo"
    )
    assert video["platforms"] == ["facebook", "tiktok", "instagram", "youtube"]


def test_recommender_keeps_non_sales_short_video_default_platform_order() -> None:
    result = content_intake.recommend_formats(
        "ลองใช้ AI ทำตัวละคร 5 รูปแล้วหน้าไม่เหมือนกัน ทำไมถึงเปลี่ยน"
    )

    video = next(
        item for item in result["options"] if item["id"] == "short_video_demo"
    )
    assert video["platforms"] == ["tiktok", "instagram", "youtube"]


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


def test_recommender_prefers_promo_post_for_ebook_link() -> None:
    result = content_intake.recommend_formats(
        "สร้างโพสต์โปรโมต ebook https://example.com/book"
    )

    assert len(result["options"]) == 4
    assert result["recommended_format"] == "promo_post"
    assert result["options"][0]["goal"] == "conversion"
    assert result["options"][0]["needs_video"] is False
    assert result["miniboss"]["score"] >= 60


def test_find_recommendation_rejects_unknown_format() -> None:
    try:
        content_intake.find_recommendation("AI idea", "podcast")
    except ValueError as exc:
        assert "Unknown recommendation format" in str(exc)
    else:
        raise AssertionError("unknown format should fail")


def test_payment_explainer_with_shopee_link_prefers_carousel() -> None:
    idea = (
        "ทางการชำระเงินบน Shopee ที่ผู้ใช้งานสามารถเลือกซื้อก่อน "
        "จ่ายทีหลัง หรือผ่อนชำระได้ตามสิทธิ์และเงื่อนไขที่แต่ละคนได้รับ "
        "https://u.shopee.co.th/SPonKpB"
    )
    result = content_intake.recommend_formats(idea)

    assert result["recommended_format"] == "carousel"
    assert result["options"][0]["goal"] == "education"
    assert all(option["id"] != "promo_post" for option in result["options"])


def test_explicit_promotion_remains_sales_with_payment_terms() -> None:
    result = content_intake.recommend_formats(
        "โปรโมตสินค้า ซื้อก่อนจ่ายทีหลัง พร้อมลิงก์สั่งซื้อ https://example.com/item"
    )

    assert result["recommended_format"] == "promo_post"
    assert result["options"][0]["goal"] == "conversion"


def test_payment_explainer_without_link_prefers_carousel() -> None:
    result = content_intake.recommend_formats(
        "อธิบายเงื่อนไขการผ่อนชำระและสิทธิ์ซื้อก่อนจ่ายทีหลัง"
    )

    assert result["recommended_format"] == "carousel"
