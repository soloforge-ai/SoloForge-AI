from __future__ import annotations

import pytest

from backend.asset_forge.backend import content_generation


def test_semantic_fidelity_rejects_body_that_loses_telegram_subject() -> None:
    package = {
        "hook": "รู้หรือยัง Bot Telegram เป็นได้มากกว่าแอดมินกลุ่ม",
        "script": "วันนี้เราจะจับเวลาเพื่อดูว่าเครื่องมือนี้ช่วยประหยัดเวลาได้จริงไหม",
        "caption": "เทียบเวลา คุณภาพ และงานที่ยังต้องแก้เอง",
        "cta": "อยากให้ทดสอบเครื่องมือไหนต่อ ส่งชื่อมาได้เลย",
        "onscreen_text": ["จับเวลาก่อนใช้", "เทียบเวลา + คุณภาพ"],
    }

    result = content_generation._semantic_fidelity(
        "รู้หรือยัง Bot Telegram เป็นได้มากกว่าแอดมินกลุ่ม สร้างรายได้มากกว่าที่คิด",
        package,
    )

    assert result["status"] == "FAIL"
    assert "telegram" in result["required_anchors"]
    assert result["matched_anchors"] == []


def test_semantic_fidelity_accepts_body_that_preserves_telegram_subject() -> None:
    package = {
        "hook": "Telegram Bot ทำอะไรได้มากกว่าตอบแชท?",
        "script": (
            "Telegram Bot สามารถรับ lead คัดกรองข้อมูล แจ้งเตือนแอดมิน "
            "และเชื่อม workflow สำหรับบริการที่สร้างรายได้ได้"
        ),
        "caption": "ตัวอย่างการต่อ Telegram Bot ให้กลายเป็น automation workflow",
        "cta": "อยากดู flow แบบไหนต่อ บอกโจทย์มาได้เลย",
        "onscreen_text": ["Telegram Bot", "Lead → Qualify → Notify"],
    }

    result = content_generation._semantic_fidelity(
        "รู้หรือยัง Bot Telegram เป็นได้มากกว่าแอดมินกลุ่ม สร้างรายได้มากกว่าที่คิด",
        package,
    )

    assert result["status"] == "PASS"
    assert "telegram" in result["matched_anchors"]


def test_missing_provider_is_non_retryable_and_never_reaches_review(monkeypatch) -> None:
    patches = []

    monkeypatch.setattr(
        content_generation,
        "feedback_for_candidate",
        lambda **_: {
            "state": "INSUFFICIENT_DATA",
            "version": "performance_feedback_v0.1",
            "sample_size": 0,
        },
    )
    monkeypatch.setattr(content_generation, "_call_provider", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(content_generation, "_send_telegram", lambda _text: None)

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        patches.append((method, path, body, prefer))
        return []

    monkeypatch.setattr(content_generation, "_supabase_request", fake_request)

    ok = content_generation._process_claimed_job(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "idea_flow_id": "CQG-1",
            "idea": "Telegram Bot automation",
            "retry_count": 0,
            "content_package": {
                "format": "question_post",
                "target_platforms": ["facebook"],
            },
        }
    )

    assert ok is False
    failure = next(body for method, _path, body, _prefer in patches if method == "PATCH")
    assert failure["status"] == "GENERATION_FAILED"
    assert failure["retry_count"] == 1
    assert "refusing template fallback" in failure["error_message"]


def test_enforce_semantic_fidelity_raises_non_retryable_error() -> None:
    with pytest.raises(
        content_generation.NonRetryableGenerationError,
        match="semantic fidelity",
    ):
        content_generation._enforce_semantic_fidelity(
            "Telegram Bot automation",
            {
                "script": "จับเวลาแล้วเปรียบเทียบคุณภาพงาน",
                "caption": "รีวิวเครื่องมือแบบไม่เดา",
                "cta": "ส่งชื่อเครื่องมือมาได้เลย",
                "onscreen_text": [],
            },
        )



def test_provider_defaults_use_current_gemini_and_pollinations_models() -> None:
    providers = {
        provider: {
            "key_env": key_env,
            "model_env": model_env,
            "default_model": default_model,
            "endpoint": endpoint,
        }
        for provider, key_env, model_env, default_model, endpoint
        in content_generation.PROVIDERS
    }

    assert providers["gemini"]["default_model"] == "gemini-3.5-flash-lite"
    assert providers["pollinations"]["default_model"] == "openai/gpt-5.4-nano"


def test_pollinations_publishable_key_is_not_used_for_server_generation(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("POLLINATIONS_API_KEY", "pk_example_publishable_key")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("publishable Pollinations key must not reach generation endpoint")

    monkeypatch.setattr(content_generation.urllib.request, "urlopen", fail_urlopen)

    result = content_generation._call_provider(
        "Telegram Bot automation",
        {"format": "question_post", "target_platforms": ["facebook"]},
    )

    assert result is None



def _facebook_context() -> dict:
    return {
        "channel": "facebook_personal",
        "voice_profile": "facebook_personal_voice_v1",
        "target_platforms": ["facebook_personal"],
        "source_context": {
            "visible_benefits": [
                "Member coupon: 40% off up to 100 THB",
                "ShopeeFood coupon: 50% off up to 70 THB",
            ]
        },
        "revenue_opportunity": {
            "affiliate_link": "https://s.shopee.co.th/example",
        },
    }


def _facebook_package(**overrides) -> dict:
    package = {
        "hook": "เห็นสิทธิ ShopeeVIP แล้วเราเอามาสรุปไว้ให้ดูง่าย ๆ",
        "script": "",
        "caption": (
            "เราเห็นข้อมูลในหน้าที่แนบมาว่ามีส่วนลด 40% สูงสุด 100 บาท "
            "และ ShopeeFood 50% สูงสุด 70 บาท เลยสรุปตัวเลขตามหน้าที่เห็นไว้ให้"
        ),
        "cta": "ลองเช็กสิทธิของตัวเองได้จากพิกัดในคอมเมนต์",
        "comment_text": (
            "พิกัด ShopeeVIP: https://s.shopee.co.th/example"
        ),
        "affiliate_placement": "comment",
        "onscreen_text": [],
    }
    package.update(overrides)
    return package


def test_facebook_voice_qa_accepts_supported_personal_post() -> None:
    result = content_generation._facebook_voice_qa(
        _facebook_package(),
        _facebook_context(),
    )

    assert result["status"] == "PASS"
    assert result["version"] == "facebook_voice_qa_v1"
    assert result["failures"] == []


@pytest.mark.parametrize("term", ["ผม", "ครับ"])
def test_facebook_voice_qa_rejects_banned_voice_terms(term: str) -> None:
    package = _facebook_package(
        caption=f"เราเห็นข้อมูลตามหน้าที่แนบมาแล้ว {term}"
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert any(item.startswith("banned_voice_terms:") for item in result["failures"])


def test_facebook_voice_qa_requires_เรา() -> None:
    package = _facebook_package(
        hook="สรุปสิทธิ ShopeeVIP จากหน้าที่แนบมา",
        caption="มีส่วนลด 40% สูงสุด 100 บาท และ ShopeeFood 50% สูงสุด 70 บาท",
        cta="เช็กสิทธิได้จากพิกัดในคอมเมนต์",
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "missing_first_person_เรา" in result["failures"]


def test_facebook_voice_qa_rejects_suspicious_encoding() -> None:
    package = _facebook_package(
        caption="เราไล่ดูข้อมูลครôm ๆ จากหน้าที่แนบมา"
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "suspicious_character_encoding" in result["failures"]


def test_facebook_voice_qa_requires_affiliate_link_in_comment() -> None:
    package = _facebook_package(
        comment_text="พิกัด ShopeeVIP อยู่ในคอมเมนต์นี้"
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "affiliate_link_missing_from_comment" in result["failures"]


def test_facebook_voice_qa_rejects_affiliate_link_in_caption_when_comment_expected() -> None:
    package = _facebook_package(
        caption=(
            "เราเห็นข้อมูลตามหน้าที่แนบมา "
            "https://s.shopee.co.th/example"
        )
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "affiliate_link_leaked_outside_comment" in result["failures"]


def test_facebook_voice_qa_rejects_unsupported_discount_claim() -> None:
    package = _facebook_package(
        caption=(
            "เราเห็นข้อมูลตามหน้าที่แนบมา และมีส่วนลด 90% สูงสุด 999 บาท"
        )
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "unsupported_percentage_claims:90" in result["failures"]
    assert "unsupported_money_claims:999" in result["failures"]


def test_facebook_voice_qa_rejects_unsupported_personal_experience() -> None:
    package = _facebook_package(
        hook="เราเพิ่งลองกดเข้า ShopeeVIP แล้วเห็นคูปองขึ้นมา"
    )

    result = content_generation._facebook_voice_qa(
        package,
        _facebook_context(),
    )

    assert result["status"] == "FAIL"
    assert "unsupported_personal_experience" in result["failures"]


def test_facebook_voice_qa_allows_personal_experience_with_source_evidence() -> None:
    context = _facebook_context()
    context["source_context"]["personal_experience"] = (
        "User explicitly stated they opened the ShopeeVIP page."
    )
    package = _facebook_package(
        hook="เราเพิ่งลองกดเข้า ShopeeVIP แล้วเห็นคูปองขึ้นมา"
    )

    result = content_generation._facebook_voice_qa(package, context)

    assert result["status"] == "PASS"


def test_enforce_facebook_voice_qa_is_non_retryable() -> None:
    with pytest.raises(
        content_generation.NonRetryableGenerationError,
        match="facebook_voice_qa_v1",
    ):
        content_generation._enforce_facebook_voice_qa(
            _facebook_package(caption="ผมสรุปไว้ให้ครับ"),
            _facebook_context(),
        )
