from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from memory import DecisionMemory, DecisionMemoryStore


@dataclass(frozen=True)
class CharacterDNA:
    character_id: str
    version: str
    height_cm: int
    style: str
    default_outfit: str
    glasses_required: bool
    wings_allowed: bool


class CharacterMemoryService:
    """Character DNA consumer backed by the model-independent Decision Memory contract."""

    def __init__(self, decision_store: DecisionMemoryStore):
        self.decision_store = decision_store

    def approve_character_dna(
        self,
        *,
        character_id: str,
        version: str,
        height_cm: int,
        style: str,
        default_outfit: str,
        glasses_required: bool,
        wings_allowed: bool,
        reason: str,
    ) -> list[DecisionMemory]:
        scope = character_id.lower()
        values = {
            "active_version": version,
            "height_cm": str(height_cm),
            "style": style,
            "default_outfit": default_outfit,
            "glasses_required": _bool_string(glasses_required),
            "wings_allowed": _bool_string(wings_allowed),
        }

        records: list[DecisionMemory] = []
        for field, value in values.items():
            key = f"character.{scope}.{field}"
            records.append(
                self.decision_store.approve(
                    subject=key,
                    decision_key=key,
                    decision=value,
                    reason=reason,
                    scope=scope,
                )
            )
        return records

    def retrieve_character_dna(self, character_id: str) -> Optional[CharacterDNA]:
        scope = character_id.lower()
        fields = {
            field: self.decision_store.retrieve_active(
                decision_key=f"character.{scope}.{field}",
                scope=scope,
            )
            for field in (
                "active_version",
                "height_cm",
                "style",
                "default_outfit",
                "glasses_required",
                "wings_allowed",
            )
        }

        if all(record is None for record in fields.values()):
            return None
        missing = [field for field, record in fields.items() if record is None]
        if missing:
            raise ValueError(
                f"Incomplete Character DNA for {character_id!r}; missing: {', '.join(missing)}"
            )

        return CharacterDNA(
            character_id=scope,
            version=fields["active_version"].content.decision,
            height_cm=int(fields["height_cm"].content.decision),
            style=fields["style"].content.decision,
            default_outfit=fields["default_outfit"].content.decision,
            glasses_required=_parse_bool(fields["glasses_required"].content.decision),
            wings_allowed=_parse_bool(fields["wings_allowed"].content.decision),
        )


def _bool_string(value: bool) -> str:
    return "true" if value else "false"


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Invalid boolean Character DNA value: {value!r}")
