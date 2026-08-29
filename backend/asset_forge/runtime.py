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
)
_GENERIC_CANONICAL_KEYS = frozenset((*_GENERIC_MASTER_KEYS, "human_female", "human_male"))

_GENERIC_REFERENCE_SOURCE = """CHARACTER REFERENCE:
- The attached master reference image is authoritative for the character's face, hairstyle, eye colors, skin tone, costume, proportions, and signature accessories.
- Preserve those core identity features consistently in every cell.
- IMPORTANT: Do NOT preserve or copy any wings, halo, angel features, bird wings, or other fantasy appendages that may appear in the reference image. The SoloForge AI CEO character has NO wings.
- The CEO must always appear as a human-like cute 3D chibi male mascot with no wings and no halo.
- Only change pose, facial expression, and gesture as needed for the sticker pack.
"""

_GENERIC_REFERENCE_REPLACEMENT = """CHARACTER REFERENCE:
- The attached canonical master reference is authoritative for the character type, face design, proportions, silhouette, and signature structural features.
- Preserve those identity features consistently in every cell.
- If the character request includes an explicit color adjective, the requested color is authoritative and may override fur, body, skin, clothing, or accent colors shown in the master reference as appropriate for that character.
- Do not reinterpret this generic character as the SoloForge CEO and do not apply CEO-specific gender, wing, halo, costume, or identity rules.
- Only change pose, facial expression, gesture, and requested color treatment as needed for the sticker pack.
"""


def _canonical_master_character(character: str) -> str:
    """Map supported generic characters to one approved canonical master reference."""
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

    # Preserve named SoloForge IP (CEO, Pearli, Aira) and unsupported generic
    # characters on the existing exact-reference / no-reference path.
    return character


def _is_generic_master_request(character: str) -> bool:
    return _canonical_master_character(character) in _GENERIC_CANONICAL_KEYS


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

    if has_reference and _is_generic_master_request(request.character):
        if _GENERIC_REFERENCE_SOURCE not in base_prompt:
            raise RuntimeError("Generic reference prompt contract changed; refusing to apply an unsafe partial rewrite.")
        base_prompt = base_prompt.replace(
            _GENERIC_REFERENCE_SOURCE,
            _GENERIC_REFERENCE_REPLACEMENT,
            1,
        )

    memory_context = character_memory_bridge.prompt_context(request.character)
    if not memory_context:
        return base_prompt
    return f"{base_prompt}\n\n{memory_context}"


asset_forge_main._load_character_reference = _master_aware_load_character_reference
asset_forge_main._build_prompt = _memory_aware_build_prompt
asset_forge_main._process_sheet = quality_process_sheet
app = asset_forge_main.app
