"""Private Chat Prawtwan endpoint backed by a Pollinations managed agent."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)

router = APIRouter(prefix="/v1/prawtwan", tags=["prawtwan"])

PRAWTWAN_MODEL = "soloforge-ai/prawtwan"
POLLINATIONS_CHAT_URL = "https://gen.pollinations.ai/v1/chat/completions"
_MAX_MESSAGES = 20
_MAX_TOTAL_CHARACTERS = 120_000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=50_000)


class PrawtwanChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=_MAX_MESSAGES)

    @model_validator(mode="after")
    def validate_total_size(self) -> "PrawtwanChatRequest":
        total = sum(len(message.content) for message in self.messages)
        if total > _MAX_TOTAL_CHARACTERS:
            raise ValueError("Chat context is too large. Clear the chat or send a shorter excerpt.")
        return self


class PrawtwanChatResponse(BaseModel):
    message: str


def _extract_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("response is not an object")

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response has no choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("choice is not an object")

    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("choice has no message")

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        combined = "".join(text_parts).strip()
        if combined:
            return combined

    raise ValueError("message content is empty or unsupported")


@router.post("/chat", response_model=PrawtwanChatResponse)
def chat_with_prawtwan(
    request: PrawtwanChatRequest,
    authorization: str | None = Header(default=None),
) -> PrawtwanChatResponse:
    """Send session-only conversation context to the private Prawtwan agent."""

    access_token = get_pollinations_access_token_from_authorization(authorization)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Connect Pollinations before using Chat Prawtwan.",
        )

    payload = {
        "model": PRAWTWAN_MODEL,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
        "stream": False,
    }

    upstream_request = urllib.request.Request(
        POLLINATIONS_CHAT_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SoloForge-Chat-Prawtwan/0.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(upstream_request, timeout=120) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # Do not surface upstream response bodies: they may contain private input.
        raise HTTPException(
            status_code=502,
            detail=f"Prawtwan request failed upstream ({exc.code}).",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=504,
            detail="Prawtwan did not respond in time.",
        ) from exc

    try:
        upstream_payload = json.loads(raw.decode("utf-8"))
        text = _extract_text(upstream_payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Prawtwan returned an invalid response.",
        ) from exc

    return PrawtwanChatResponse(message=text)
