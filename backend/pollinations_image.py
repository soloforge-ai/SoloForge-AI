"""SoloForge Pollinations image generation boundary.

This module is intentionally transport-focused. The Pollinations credential must
be supplied through the Render environment and never committed to Git.

Memory integration is optional and additive: callers that do not provide memory
services keep the existing behavior. Event Memory records generation outcomes,
while Character Memory can enrich prompts with approved ACTIVE Character DNA.
"""

from __future__ import annotations

import os
from time import perf_counter
from typing import Any, Optional
from uuid import uuid4

import requests

try:
    from .character_memory import CharacterMemoryService
    from .memory import EventMemoryStore, MemoryEventName
except ImportError:  # Allows direct execution/import from the backend directory.
    from character_memory import CharacterMemoryService
    from memory import EventMemoryStore, MemoryEventName


POLLINATIONS_IMAGE_URL = os.getenv(
    "POLLINATIONS_IMAGE_URL", "https://gen.pollinations.ai/image"
)
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")


def generate_image(
    payload: dict[str, Any],
    *,
    event_store: Optional[EventMemoryStore] = None,
    character_memory: Optional[CharacterMemoryService] = None,
) -> dict[str, Any]:
    """Generate one image with optional Event and Character Memory integration.

    Existing callers can keep calling ``generate_image(payload)`` unchanged.
    Character DNA is applied only when both ``character_id`` is present in the
    payload and a CharacterMemoryService is injected by the caller.
    """

    generation_id = str(payload.get("generation_id") or f"img-{uuid4().hex}")
    task_id = _optional_string(payload.get("task_id"))
    model = str(payload.get("model", "gpt-image-2"))
    character_id = _optional_string(payload.get("character_id"))
    started_at = perf_counter()

    try:
        if not POLLINATIONS_API_KEY:
            raise RuntimeError("POLLINATIONS_API_KEY is not configured")

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("prompt is required")

        character_dna_version: Optional[str] = None
        if character_id is not None and character_memory is not None:
            dna = character_memory.retrieve_character_dna(character_id)
            if dna is None:
                raise ValueError(
                    f"No ACTIVE Character DNA found for character_id={character_id!r}"
                )
            prompt = _apply_character_dna(prompt, dna)
            character_dna_version = dna.version

        params = {
            "model": model,
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

        result = {
            "generation_id": generation_id,
            "url": response.url,
            "model": params["model"],
            "width": params["width"],
            "height": params["height"],
        }
        if character_id is not None and character_dna_version is not None:
            result["character_id"] = character_id.lower()
            result["character_dna_version"] = character_dna_version

        metrics: dict[str, Any] = {
            "width": params["width"],
            "height": params["height"],
        }
        if character_id is not None and character_dna_version is not None:
            metrics["character_id"] = character_id.lower()
            metrics["character_dna_version"] = character_dna_version

        _append_event(
            event_store,
            event_name=MemoryEventName.IMAGE_GENERATED,
            generation_id=generation_id,
            result="success",
            task_id=task_id,
            model=params["model"],
            duration_ms=_elapsed_ms(started_at),
            output_refs=[response.url],
            metrics=metrics,
        )
        return result

    except Exception as exc:
        _append_event(
            event_store,
            event_name=MemoryEventName.ERROR_OCCURRED,
            generation_id=generation_id,
            result="failed",
            task_id=task_id,
            model=model,
            duration_ms=_elapsed_ms(started_at),
            error={
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise


def _apply_character_dna(prompt: str, dna: Any) -> str:
    rules = [
        "APPROVED ACTIVE CHARACTER DNA — MUST PRESERVE:",
        f"- Character ID: {dna.character_id}",
        f"- Character DNA version: {dna.version}",
        f"- Height: {dna.height_cm} cm",
        f"- Visual style: {dna.style}",
        f"- Default outfit: {dna.default_outfit}",
        f"- Glasses required: {'yes' if dna.glasses_required else 'no'}",
        f"- Wings allowed: {'yes' if dna.wings_allowed else 'no'}",
    ]
    if not dna.wings_allowed:
        rules.append("- Do not generate wings, feathers attached to the body, or a halo.")

    return f"{prompt}\n\n" + "\n".join(rules)


def _append_event(
    event_store: Optional[EventMemoryStore],
    *,
    event_name: MemoryEventName,
    generation_id: str,
    result: str,
    task_id: Optional[str],
    model: str,
    duration_ms: int,
    output_refs: Optional[list[str]] = None,
    metrics: Optional[dict[str, Any]] = None,
    error: Optional[dict[str, Any]] = None,
) -> None:
    if event_store is None:
        return

    event_store.append(
        event_name=event_name,
        actor="pollinations_image",
        entity_type="image_generation",
        entity_id=generation_id,
        result=result,
        subject=f"image_generation.{generation_id}",
        task_id=task_id,
        model=model,
        provider="pollinations",
        output_refs=output_refs,
        metrics=metrics,
        error=error,
        duration_ms=duration_ms,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))


def _optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
