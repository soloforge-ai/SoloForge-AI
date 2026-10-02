from __future__ import annotations

import io
import json
import urllib.error

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



class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._payload


def _provider_payload() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "hook": "Telegram Bot ทำอะไรได้มากกว่าตอบแชท?",
                            "script": "Telegram Bot ช่วยรับ lead และต่อ automation workflow ได้",
                            "caption": "ใช้ Telegram Bot เชื่อม workflow งานจริง",
                            "cta": "อยากดู flow แบบไหนต่อ?",
                            "onscreen_text": ["Telegram Bot", "Automation"],
                            "visual_prompt": "Telegram automation workflow",
                            "motion_prompt": "subtle interface motion",
                            "risk_level": "LOW",
                        }
                    )
                }
            }
        ]
    }


def test_transient_provider_503_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    calls = 0
    sleeps: list[int] = []

    def fake_urlopen(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise urllib.error.HTTPError(
                url="https://example.invalid",
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=io.BytesIO(b""),
            )
        return _FakeResponse(_provider_payload())

    monkeypatch.setattr(content_generation.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(content_generation.time, "sleep", sleeps.append)

    result = content_generation._call_provider(
        "Telegram Bot automation",
        {"format": "question_post", "target_platforms": ["facebook"]},
    )

    assert result is not None
    _package, provider, model = result
    assert provider == "gemini"
    assert model == "gemini-3.5-flash-lite"
    assert calls == 3
    assert sleeps == [1, 2]


def test_non_transient_provider_404_does_not_retry(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    calls = 0
    sleeps: list[int] = []

    def fake_urlopen(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            url="https://example.invalid",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr(content_generation.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(content_generation.time, "sleep", sleeps.append)

    result = content_generation._call_provider(
        "Telegram Bot automation",
        {"format": "question_post", "target_platforms": ["facebook"]},
    )

    assert result is None
    assert calls == 1
    assert sleeps == []


def test_transient_provider_stops_after_max_attempts(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    calls = 0
    sleeps: list[int] = []

    def fake_urlopen(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            url="https://example.invalid",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr(content_generation.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(content_generation.time, "sleep", sleeps.append)

    result = content_generation._call_provider(
        "Telegram Bot automation",
        {"format": "question_post", "target_platforms": ["facebook"]},
    )

    assert result is None
    assert calls == content_generation.PROVIDER_MAX_ATTEMPTS
    assert sleeps == [1, 2]



def test_provider_fallback_runs_after_transient_retry_exhaustion(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)

    calls: list[str] = []
    sleeps: list[int] = []

    def fake_urlopen(req, **_kwargs):
        host = req.full_url
        calls.append(host)
        if "generativelanguage.googleapis.com" in host:
            raise urllib.error.HTTPError(
                url=host,
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=io.BytesIO(b""),
            )
        if "api.groq.com" in host:
            return _FakeResponse(_provider_payload())
        raise AssertionError(f"unexpected provider URL: {host}")

    monkeypatch.setattr(content_generation.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(content_generation.time, "sleep", sleeps.append)

    result = content_generation._call_provider(
        "Telegram Bot automation",
        {"format": "question_post", "target_platforms": ["facebook"]},
    )

    assert result is not None
    _package, provider, _model = result
    assert provider == "groq"
    assert sum("generativelanguage.googleapis.com" in url for url in calls) == 3
    assert sum("api.groq.com" in url for url in calls) == 1
    assert sleeps == [1, 2]
