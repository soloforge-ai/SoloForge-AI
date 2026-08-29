from __future__ import annotations

import main as asset_forge_main

from backend.character_memory_bridge import AssetForgeCharacterMemoryBridge
from backend.output_quality import process_sheet as quality_process_sheet

character_memory_bridge = AssetForgeCharacterMemoryBridge()
_original_build_prompt = asset_forge_main._build_prompt
_original_load_character_reference = asset_forge_main._load_character_reference


_GENERIC_MASTER_KEYS = (
    "cat",
    "dog",
    "bear",
    "rabbit",
    "robot",
)


def _canonical_master_character(character: str) -> str:
    """Map user-configured generic characters to one canonical master reference."""
    normalized = character.strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())

    if "female human" in normalized or "human female" in normalized:
        return "human_female"
    if "male human" in normalized or "human male" in normalized:
        return "human_male"

    tokens = set(normalized.split())
    for key in _GENERIC_MASTER_KEYS:
        if key in tokens:
            return key

    # Preserve named SoloForge IP (CEO, Pearli, Aira) and any future exact keys.
    return character


def _master_aware_load_character_reference(character: str) -> bytes | None:
    canonical = _canonical_master_character(character)
    reference = _original_load_character_reference(canonical)
    if reference is not None:
        return reference

    if canonical != character:
        return _original_load_character_reference(character)
    return None


def _memory_aware_build_prompt(request, columns: int, rows: int, has_reference: bool) -> str:
    base_prompt = _original_build_prompt(request, columns, rows, has_reference)
    memory_context = character_memory_bridge.prompt_context(request.character)
    if not memory_context:
        return base_prompt
    return f"{base_prompt}\n\n{memory_context}"


asset_forge_main._load_character_reference = _master_aware_load_character_reference
asset_forge_main._build_prompt = _memory_aware_build_prompt
asset_forge_main._process_sheet = quality_process_sheet
app = asset_forge_main.app
