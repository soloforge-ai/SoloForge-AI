from __future__ import annotations

from backend.asset_forge.backend import asset_provider


def test_generate_asset_uses_local_fallback_when_pollinations_missing(monkeypatch) -> None:
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
    monkeypatch.setenv("CONTENT_ASSET_WIDTH", "640")
    monkeypatch.setenv("CONTENT_ASSET_HEIGHT", "800")

    data, meta = asset_provider.generate_asset(
        "editorial AI visual",
        fallback_title="ทดสอบระบบสร้างภาพสำรอง",
        fallback_subtitle="ต้องทำงานต่อได้แม้ไม่มีเครดิต",
    )

    assert data.startswith(b"\x89PNG")
    assert meta["provider"] == "local_template"
    assert meta["mode"] == "deterministic_fallback"
    assert meta["attempts"][0]["provider"] == "pollinations"
    assert meta["attempts"][0]["result"] == "failed"
    assert meta["attempts"][-1] == {
        "provider": "local_template",
        "result": "success",
    }


def test_generate_asset_prefers_pollinations_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        asset_provider,
        "_pollinations_image",
        lambda prompt: b"fake-image-bytes",
    )

    data, meta = asset_provider.generate_asset(
        "prompt",
        fallback_title="fallback",
    )

    assert data == b"fake-image-bytes"
    assert meta["provider"] == "pollinations"
    assert meta["mode"] == "ai_generated"
    assert meta["attempts"] == [
        {"provider": "pollinations", "result": "success"}
    ]


def test_template_image_is_deterministic_png(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_ASSET_WIDTH", "640")
    monkeypatch.setenv("CONTENT_ASSET_HEIGHT", "800")

    first = asset_provider._template_image(
        title="AI HACKWORK",
        subtitle="Fallback visual",
    )
    second = asset_provider._template_image(
        title="AI HACKWORK",
        subtitle="Fallback visual",
    )

    assert first.startswith(b"\x89PNG")
    assert first == second
