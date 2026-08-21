from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    ARCHIVED = "ARCHIVED"


@dataclass
class DecisionContent:
    decision_key: str
    decision: str
    reason: str
    authority: str = "project_owner"
    scope: Optional[str] = None


@dataclass
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

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

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


class DecisionMemoryStore(ABC):
    @abstractmethod
    def approve(
        self,
        *,
        subject: str,
        decision_key: str,
        decision: str,
        reason: str,
        scope: Optional[str] = None,
        authority: str = "project_owner",
        source: str = "human_approval",
        version: str = "1.0",
    ) -> DecisionMemory:
        raise NotImplementedError

    @abstractmethod
    def retrieve_active(
        self,
        *,
        decision_key: str,
        scope: Optional[str] = None,
    ) -> Optional[DecisionMemory]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[DecisionMemory]:
        raise NotImplementedError


class JsonDecisionMemoryStore(DecisionMemoryStore):
    """Transparent local Decision Memory MVP backed by one JSON file.

    The storage boundary is intentionally simple. Consumers depend on the
    DecisionMemoryStore contract so the persistence layer can be replaced later
    without changing retrieval semantics.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def approve(
        self,
        *,
        subject: str,
        decision_key: str,
        decision: str,
        reason: str,
        scope: Optional[str] = None,
        authority: str = "project_owner",
        source: str = "human_approval",
        version: str = "1.0",
    ) -> DecisionMemory:
        if authority != "project_owner":
            raise ValueError(
                "Decision Memory v1 only allows project_owner authority "
                "for authoritative ACTIVE decisions."
            )

        records = self.list_all()
        now = _utc_now()
        previous = _find_active(records, decision_key=decision_key, scope=scope)

        if previous is not None:
            previous.status = MemoryStatus.SUPERSEDED
            previous.updated_at = now

        record = DecisionMemory(
            id=f"dec-{uuid4().hex}",
            type="decision",
            subject=subject,
            content=DecisionContent(
                decision_key=decision_key,
                decision=decision,
                reason=reason,
                authority=authority,
                scope=scope,
            ),
            source=source,
            created_at=now,
            updated_at=now,
            status=MemoryStatus.ACTIVE,
            version=version,
            supersedes=previous.id if previous is not None else None,
        )

        records.append(record)
        self._write_all(records)
        return record

    def retrieve_active(
        self,
        *,
        decision_key: str,
        scope: Optional[str] = None,
    ) -> Optional[DecisionMemory]:
        return _find_active(
            self.list_all(),
            decision_key=decision_key,
            scope=scope,
        )

    def list_all(self) -> list[DecisionMemory]:
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Decision memory store must contain a JSON list.")

        return [DecisionMemory.from_dict(item) for item in raw]

    def _write_all(self, records: Iterable[DecisionMemory]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.to_dict() for record in records]

        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise


def _find_active(
    records: Iterable[DecisionMemory],
    *,
    decision_key: str,
    scope: Optional[str],
) -> Optional[DecisionMemory]:
    matches = [
        record
        for record in records
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
