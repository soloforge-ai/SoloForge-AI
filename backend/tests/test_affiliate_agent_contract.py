from __future__ import annotations

import json
from io import BytesIO

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
