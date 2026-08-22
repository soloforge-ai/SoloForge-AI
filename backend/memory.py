from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    ARCHIVED = "ARCHIVED"


class MemoryEventName(str, Enum):
    PRODUCT_ANALYZED = "PRODUCT_ANALYZED"
    PROMPT_GENERATED = "PROMPT_GENERATED"
    IMAGE_GENERATED = "IMAGE_GENERATED"
    VIDEO_GENERATED = "VIDEO_GENERATED"
    OUTPUT_ACCEPTED = "OUTPUT_ACCEPTED"
    OUTPUT_REJECTED = "OUTPUT_REJECTED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    ERROR_RESOLVED = "ERROR_RESOLVED"
    DECISION_APPROVED = "DECISION_APPROVED"
    VERSION_SUPERSEDED = "VERSION_SUPERSEDED"
    CONTENT_PUBLISHED = "CONTENT_PUBLISHED"
    PERFORMANCE_RECORDED = "PERFORMANCE_RECORDED"


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


@dataclass
class EventContent:
    event_name: MemoryEventName
    actor: str
    entity_type: str
    entity_id: str
    result: str
    task_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    input_refs: Optional[list[str]] = None
    output_refs: Optional[list[str]] = None
    metrics: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    duration_ms: Optional[int] = None


@dataclass
class MemoryEvent:
    id: str
    type: str
    subject: str
    content: EventContent
    source: str
    created_at: str
    updated_at: str
    status: MemoryStatus
    version: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["content"]["event_name"] = self.content.event_name.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "MemoryEvent":
        content = dict(payload["content"])
        content["event_name"] = MemoryEventName(content["event_name"])
        return cls(
            id=payload["id"],
            type=payload["type"],
            subject=payload["subject"],
            content=EventContent(**content),
            source=payload["source"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            status=MemoryStatus(payload["status"]),
            version=payload["version"],
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


class EventMemoryStore(ABC):
    @abstractmethod
    def append(
        self,
        *,
        event_name: MemoryEventName,
        actor: str,
        entity_type: str,
        entity_id: str,
        result: str,
        subject: Optional[str] = None,
        source: str = "system_observation",
        version: str = "1.0",
        task_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        input_refs: Optional[list[str]] = None,
        output_refs: Optional[list[str]] = None,
        metrics: Optional[dict[str, Any]] = None,
        error: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> MemoryEvent:
        raise NotImplementedError

    @abstractmethod
    def retrieve(
        self,
        *,
        event_name: Optional[MemoryEventName] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[MemoryEvent]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[MemoryEvent]:
        raise NotImplementedError


class JsonDecisionMemoryStore(DecisionMemoryStore):
    """Transparent local Decision Memory MVP backed by one JSON file."""

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
        _write_json_records(self.path, [item.to_dict() for item in records])
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
        raw = _read_json_list(self.path, "Decision memory store")
        return [DecisionMemory.from_dict(item) for item in raw]


class JsonEventMemoryStore(EventMemoryStore):
    """Append-only Memory Event MVP backed by one JSON file.

    Events record what happened. Existing events are never mutated through this
    store, keeping observation history independent from Decision Memory.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(
        self,
        *,
        event_name: MemoryEventName,
        actor: str,
        entity_type: str,
        entity_id: str,
        result: str,
        subject: Optional[str] = None,
        source: str = "system_observation",
        version: str = "1.0",
        task_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        input_refs: Optional[list[str]] = None,
        output_refs: Optional[list[str]] = None,
        metrics: Optional[dict[str, Any]] = None,
        error: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> MemoryEvent:
        if not actor.strip():
            raise ValueError("Memory Event actor must not be empty.")
        if not entity_type.strip():
            raise ValueError("Memory Event entity_type must not be empty.")
        if not entity_id.strip():
            raise ValueError("Memory Event entity_id must not be empty.")
        if not result.strip():
            raise ValueError("Memory Event result must not be empty.")
        if duration_ms is not None and duration_ms < 0:
            raise ValueError("Memory Event duration_ms must be non-negative.")

        records = self.list_all()
        now = _utc_now()
        record = MemoryEvent(
            id=f"evt-{uuid4().hex}",
            type="event",
            subject=subject or f"{entity_type}.{entity_id}",
            content=EventContent(
                event_name=event_name,
                actor=actor,
                entity_type=entity_type,
                entity_id=entity_id,
                result=result,
                task_id=task_id,
                model=model,
                provider=provider,
                input_refs=input_refs,
                output_refs=output_refs,
                metrics=metrics,
                error=error,
                duration_ms=duration_ms,
            ),
            source=source,
            created_at=now,
            updated_at=now,
            status=MemoryStatus.ACTIVE,
            version=version,
        )
        records.append(record)
        _write_json_records(self.path, [item.to_dict() for item in records])
        return record

    def retrieve(
        self,
        *,
        event_name: Optional[MemoryEventName] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[MemoryEvent]:
        records = self.list_all()
        matches = [
            record
            for record in records
            if (event_name is None or record.content.event_name == event_name)
            and (entity_type is None or record.content.entity_type == entity_type)
            and (entity_id is None or record.content.entity_id == entity_id)
        ]
        matches.sort(key=lambda record: record.created_at, reverse=True)

        if limit is not None:
            if limit < 0:
                raise ValueError("Memory Event retrieval limit must be non-negative.")
            matches = matches[:limit]

        return matches

    def list_all(self) -> list[MemoryEvent]:
        raw = _read_json_list(self.path, "Memory event store")
        return [MemoryEvent.from_dict(item) for item in raw]


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


def _read_json_list(path: Path, label: str) -> list[dict]:
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{label} must contain a JSON list.")
    return raw


def _write_json_records(path: Path, payload: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
