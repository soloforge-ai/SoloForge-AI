"""SoloForge Pollinations image generation boundary.

This module is intentionally transport-focused. The Pollinations credential must
be supplied through the Render environment and never committed to Git.
"""

import os
from typing import Any

import requests


POLLINATIONS_IMAGE_URL = os.getenv(
    "POLLINATIONS_IMAGE_URL", "https://gen.pollinations.ai/image"
)
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")


def generate_image(payload: dict[str, Any]) -> dict[str, Any]:
    if not POLLINATIONS_API_KEY:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")

    params = {
        "model": payload.get("model", "gpt-image-2"),
        "width": int(payload.get("width", 1024)),
        "height": int(payload.get("height", 1024)),
    }
    for key in ("seed", "negative_prompt"):
        if payload.get(key) is not None:
            params[key] = payload[key]

    response = requests.get(
        POLLINATIONS_IMAGE_URL,
        params={"prompt": prompt, **params},
        headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
        timeout=120,
    )
    response.raise_for_status()

    return {
        "url": response.url,
        "model": params["model"],
        "width": params["width"],
        "height": params["height"],
    }
