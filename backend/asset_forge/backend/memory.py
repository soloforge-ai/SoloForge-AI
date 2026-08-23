from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class DecisionContent:
    decision_key: str
    decision: str
    reason: str
    authority: str = "project_owner"
    scope: Optional[str] = None


@dataclass(frozen=True)
class DecisionMemory:
    id: str
    type: str
    subject: str
    content: DecisionContent
    source: str
    created_at: str
    updated_at: str
    status: MemoryStatus
    version: str
    supersedes: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: dict) -> "DecisionMemory":
        return cls(
            id=payload["id"],
            type=payload["type"],
            subject=payload["subject"],
            content=DecisionContent(**payload["content"]),
            source=payload["source"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            status=MemoryStatus(payload["status"]),
            version=payload["version"],
            supersedes=payload.get("supersedes"),
        )


class JsonDecisionMemoryStore:
    """Read the Memory Foundation v1 Decision Memory envelope at runtime."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def list_all(self) -> list[DecisionMemory]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Decision memory store must contain a JSON list.")
        return [DecisionMemory.from_dict(item) for item in raw]

    def retrieve_active(
        self,
        *,
        decision_key: str,
        scope: Optional[str] = None,
    ) -> Optional[DecisionMemory]:
        matches = [
            record
            for record in self.list_all()
            if record.type == "decision"
            and record.status == MemoryStatus.ACTIVE
            and record.content.decision_key == decision_key
            and record.content.scope == scope
        ]
        if len(matches) > 1:
            raise ValueError(
                "Conflicting ACTIVE Decision Memory records found for "
                f"decision_key={decision_key!r}, scope={scope!r}."
            )
        return matches[0] if matches else None
