from __future__ import annotations

import main as asset_forge_main

from backend.character_memory_bridge import AssetForgeCharacterMemoryBridge

character_memory_bridge = AssetForgeCharacterMemoryBridge()
_original_build_prompt = asset_forge_main._build_prompt


def _memory_aware_build_prompt(request, columns: int, rows: int, has_reference: bool) -> str:
    base_prompt = _original_build_prompt(request, columns, rows, has_reference)
    memory_context = character_memory_bridge.prompt_context(request.character)
    if not memory_context:
        return base_prompt
    return f"{base_prompt}\n\n{memory_context}"


asset_forge_main._build_prompt = _memory_aware_build_prompt
app = asset_forge_main.app
