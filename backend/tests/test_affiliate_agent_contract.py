from __future__ import annotations

import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.asset_forge.backend.affiliate_agent as affiliate


class _FakeResponse:
    def __init__(self, payload: object):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def _program(slug: str = "tool-a") -> dict[str, object]:
    return {
        "name": "Tool A",
        "slug": slug,
        "url": "https://example.com",
        "category": "AI",
        "description": "AI video creation tool for creators and YouTubers.",
        "commission": {
            "type": "recurring",
            "rate": "30%",
            "value": 30,
            "mode": "percentage",
        },
        "cookie_days": 60,
        "signup_url": "https://example.com/affiliate",
        "verified": True,
        "marketing_materials": True,
        "agents": {
            "keywords": ["ai-video", "creator", "youtube"],
            "use_cases": ["short-form video creators", "YouTube production"],
        },
    }


def _client(monkeypatch, list_payload=None):
    def fake_urlopen(request, timeout=0):
        if "/api/programs/" in request.full_url:
            return _FakeResponse(_program())
        return _FakeResponse(list_payload if list_payload is not None else [_program()])

    monkeypatch.setattr(affiliate.urllib.request, "urlopen", fake_urlopen)
    app = FastAPI()
    app.include_router(affiliate.router)
    return TestClient(app)


def test_discover_normalizes_openaffiliate_and_filters_cookie(monkeypatch):
    client = _client(
        monkeypatch,
        [
            _program("good"),
            {
                **_program("short-cookie"),
                "cookie_days": 7,
            },
        ],
    )

    response = client.get("/v1/affiliate/programs?min_cookie_days=30")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "good"
    assert body[0]["commission"]["type"] == "recurring"
    assert body[0]["cookie_days"] == 60
    assert body[0]["source"] == "openaffiliate"


def test_analyze_is_deterministic_and_flags_real_risk(monkeypatch):
    client = _client(monkeypatch)

    response = client.post(
        "/v1/affiliate/programs/tool-a/analyze",
        json={"niche": "AI video", "audience": "YouTube creator beginners"},
    )

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["total_score"] <= 100
    assert body["competition"] == 50.0
    assert body["audience_fit"] > 35
    assert any("Recurring commission" in item for item in body["rationale"])
    assert any("neutral" in item for item in body["risks"])
    assert body["content_angles"]


def test_content_factory_requires_connected_pollinations(monkeypatch):
    client = _client(monkeypatch)

    response = client.post(
        "/v1/affiliate/content/generate",
        json={
            "slug": "tool-a",
            "platform": "youtube_shorts",
            "format": "review",
            "intent": "commercial_investigation",
            "goal": "affiliate_click",
        },
    )

    assert response.status_code == 401
    assert "Connect Pollinations" in response.json()["detail"]


def test_content_factory_returns_structured_package_and_forces_claim_verification(monkeypatch):
    generated = {
        "title": "ลอง Tool A ทำคลิปสั้นได้แค่ไหน?",
        "hooks": [
            "AI ตัวนี้ช่วยทำวิดีโอได้จริงแค่ไหน?",
            "วันนี้จะลองให้ Tool A ช่วยทำคลิปหนึ่งชิ้น",
            "ก่อนจ่ายเงิน มาดู workflow จริงกัน",
        ],
        "script": "Tool A เป็นเครื่องมือ AI video วันนี้จะทดสอบ workflow จริงก่อนสรุปผล",
        "shot_list": ["เปิดหน้าเครื่องมือ", "ทดลองสร้างคลิป", "สรุปสิ่งที่พบ"],
        "voiceover": "วันนี้จะลอง Tool A แบบไม่สรุปล่วงหน้าว่าดีหรือไม่",
        "visual_prompts": ["clean AI video workspace, vertical 9:16"],
        "thumbnail_brief": "ข้อความสั้น: Tool A ใช้จริงเป็นไง?",
        "cta": "ถ้าอยากดูรายละเอียดโปรแกรม ลิงก์ Affiliate อยู่ในคำอธิบาย",
        "description": "ทดลอง workflow ของ Tool A และเช็กข้อจำกัดก่อนตัดสินใจ",
        "affiliate_disclosure": "มีลิงก์ Affiliate ในคำอธิบาย",
        "claims": [
            {
                "claim_text": "ประหยัดเวลาได้ 70%",
                "claim_type": "measured_result",
                "evidence_required": "",
            }
        ],
    }

    def fake_urlopen(request, timeout=0):
        if request.full_url == affiliate.POLLINATIONS_CHAT_URL:
            return _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(generated, ensure_ascii=False)
                            }
                        }
                    ]
                }
            )
        if "/api/programs/" in request.full_url:
            return _FakeResponse(_program())
        return _FakeResponse([_program()])

    monkeypatch.setattr(affiliate.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        affiliate,
        "get_pollinations_access_token_from_authorization",
        lambda _header: "pollinations-access-token",
    )

    app = FastAPI()
    app.include_router(affiliate.router)
    client = TestClient(app)

    response = client.post(
        "/v1/affiliate/content/generate",
        headers={"Authorization": "Bearer app-session"},
        json={
            "slug": "tool-a",
            "platform": "youtube_shorts",
            "format": "review",
            "intent": "commercial_investigation",
            "goal": "affiliate_click",
            "niche": "AI Creator Tools",
            "audience": "beginner creators",
            "language": "th",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == generated["title"]
    assert body["program_name"] == "Tool A"
    assert body["claims"][0]["claim_type"] == "measured_result"
    assert body["claims"][0]["verification_status"] == "unverified"
    assert "Real hands-on test evidence" in body["claims"][0]["evidence_required"]
    assert body["tools"][0]["role"] == "Script / Content Draft"
    assert body["end_card"]["closing"] == "ทดลองจริง ใช้จริง แล้วค่อยเล่า"
