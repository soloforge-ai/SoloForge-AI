import json
from urllib import request as urllib_request

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.asset_forge.backend.prawtwan_chat as prawtwan


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._body


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(prawtwan.router)
    return TestClient(app)


def test_chat_requires_connected_pollinations_session(monkeypatch):
    monkeypatch.setattr(
        prawtwan,
        "get_pollinations_access_token_from_authorization",
        lambda authorization: None,
    )

    response = _client().post(
        "/v1/prawtwan/chat",
        json={"messages": [{"role": "user", "content": "พี่พราว อยู่ไหม"}]},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Connect Pollinations before using Chat Prawtwan."


def test_chat_calls_fixed_private_agent_and_returns_text(monkeypatch):
    # Authorization substituted only for this isolated mocked legacy contract.
    monkeypatch.setattr(prawtwan, "require_interactive_chat_execution", lambda: None)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        prawtwan,
        "get_pollinations_access_token_from_authorization",
        lambda authorization: "pollinations-access-token" if authorization == "Bearer session-token" else None,
    )

    def fake_urlopen(request: urllib_request.Request, timeout: int):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "อยู่ค่ะ เอาฉากมาให้พี่อ่านได้เลย",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(prawtwan.urllib.request, "urlopen", fake_urlopen)

    response = _client().post(
        "/v1/prawtwan/chat",
        headers={"Authorization": "Bearer session-token"},
        json={
            "messages": [
                {"role": "user", "content": "พี่พราว อยู่ไหม"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "อยู่ค่ะ เอาฉากมาให้พี่อ่านได้เลย"}
    assert captured["url"] == "https://gen.pollinations.ai/v1/chat/completions"
    assert captured["timeout"] == 120
    assert captured["authorization"] == "Bearer pollinations-access-token"
    assert captured["payload"] == {
        "model": "soloforge-ai/prawtwan",
        "messages": [{"role": "user", "content": "พี่พราว อยู่ไหม"}],
        "stream": False,
    }
    assert "pollinations-access-token" not in response.text


def test_chat_rejects_oversized_context(monkeypatch):
    monkeypatch.setattr(
        prawtwan,
        "get_pollinations_access_token_from_authorization",
        lambda authorization: "unused",
    )

    response = _client().post(
        "/v1/prawtwan/chat",
        headers={"Authorization": "Bearer session-token"},
        json={
            "messages": [
                {"role": "user", "content": "x" * 50_000},
                {"role": "assistant", "content": "y" * 50_000},
                {"role": "user", "content": "z" * 21_000},
            ]
        },
    )

    assert response.status_code == 422


def test_chat_valid_session_is_fail_closed_without_spending_authorization(monkeypatch):
    from unittest.mock import Mock
    from backend.asset_forge.backend import execution_policy

    monkeypatch.setattr(prawtwan, "get_pollinations_access_token_from_authorization", lambda _: "fake-token")
    provider = Mock(side_effect=AssertionError("Provider must not be called"))
    monkeypatch.setattr(prawtwan.urllib.request, "urlopen", provider)
    response = _client().post("/v1/prawtwan/chat", headers={"Authorization": "Bearer session-token"}, json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 503
    assert "fake-token" not in response.text
    assert execution_policy.interactive_chat_execution_authorized() is False
    provider.assert_not_called()


def test_chat_and_generation_authorization_are_independently_fail_closed(monkeypatch):
    from fastapi import HTTPException
    from backend.asset_forge.backend import execution_policy
    import pytest

    assert execution_policy.interactive_chat_execution_authorized() is False
    assert execution_policy.generation_execution_authorized() is False
    with pytest.raises(HTTPException) as chat_error:
        execution_policy.require_interactive_chat_execution()
    with pytest.raises(HTTPException) as image_error:
        execution_policy.require_generation_execution()
    assert chat_error.value.status_code == 503
    assert image_error.value.status_code == 503
