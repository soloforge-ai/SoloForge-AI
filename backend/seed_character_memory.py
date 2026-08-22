from pathlib import Path

from character_memory import CharacterMemoryService
from memory import JsonDecisionMemoryStore


DEFAULT_DECISIONS_PATH = Path(__file__).parent / "data" / "memory" / "decisions.json"


def seed_ceo_character_dna(path: Path = DEFAULT_DECISIONS_PATH) -> None:
    service = CharacterMemoryService(JsonDecisionMemoryStore(path))
    existing = service.retrieve_character_dna("ceo")
    if existing is not None and existing.version == "1.0":
        return

    service.approve_character_dna(
        character_id="ceo",
        version="1.0",
        height_cm=30,
        style="3D Chibi",
        default_outfit=(
            "White Luxury Suit; Black shirt; Red tie; White pants; "
            "Black Leather shoes; Gold SoloForge Pin"
        ),
        glasses_required=True,
        wings_allowed=False,
        reason=(
            "Seeded from the approved SoloForge CEO character profile. "
            "Wings are disallowed to preserve the approved human chibi mascot identity."
        ),
    )


if __name__ == "__main__":
    seed_ceo_character_dna()
