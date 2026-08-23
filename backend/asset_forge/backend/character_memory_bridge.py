from __future__ import annotations

from pathlib import Path
from typing import Optional

from .character_memory import CharacterDNA, CharacterMemoryService
from .memory import JsonDecisionMemoryStore

DEFAULT_DECISIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "memory" / "decisions.json"
MEMORY_REQUIRED_CHARACTERS = {"ceo"}


class AssetForgeCharacterMemoryBridge:
    """Runtime bridge between Asset Forge and approved Character DNA memory."""

    def __init__(self, decisions_path: Path = DEFAULT_DECISIONS_PATH):
        self.service = CharacterMemoryService(JsonDecisionMemoryStore(decisions_path))

    def resolve(self, character: str) -> Optional[CharacterDNA]:
        key = character.strip().lower()
        dna = self.service.retrieve_character_dna(key)
        if key in MEMORY_REQUIRED_CHARACTERS and dna is None:
            raise ValueError(f"Approved Character DNA is required for {character!r} but was not found.")
        return dna

    def prompt_context(self, character: str) -> str:
        dna = self.resolve(character)
        if dna is None:
            return ""
        glasses_rule = "- Glasses are mandatory and must never be removed." if dna.glasses_required else "- Glasses are optional unless required by the reference image."
        wings_rule = "- Wings may be used only when supported by the approved reference and prompt." if dna.wings_allowed else "- NO wings, halo, feathers attached to the body, or fantasy appendages."
        return f"""APPROVED CHARACTER DNA — MEMORY FOUNDATION
- Character ID: {dna.character_id}
- Active DNA version: {dna.version}
- Canonical height: {dna.height_cm} cm
- Canonical visual style: {dna.style}
- Approved default outfit: {dna.default_outfit}
{glasses_rule}
{wings_rule}
- These ACTIVE Memory rules outrank conflicting generated details or reference artifacts."""
