from __future__ import annotations

STATUSES = (
    "CAPTURED",
    "TRIAGED",
    "RESEARCHED",
    "EVALUATED",
    "GRADUATED",
    "PARKED",
    "REJECTED",
    "EXPERIMENT",
    "VALIDATED",
    "KILLED",
)

TERMINAL_STATUSES = frozenset({"REJECTED", "VALIDATED", "KILLED"})

VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "CAPTURED": frozenset({"TRIAGED", "PARKED", "REJECTED"}),
    "TRIAGED": frozenset({"RESEARCHED", "EVALUATED", "PARKED", "REJECTED"}),
    "RESEARCHED": frozenset({"EVALUATED", "PARKED", "REJECTED"}),
    "EVALUATED": frozenset({"GRADUATED", "PARKED", "REJECTED"}),
    "GRADUATED": frozenset({"EXPERIMENT", "PARKED", "KILLED"}),
    "PARKED": frozenset({"TRIAGED", "RESEARCHED", "REJECTED"}),
    "REJECTED": frozenset(),
    "EXPERIMENT": frozenset({"VALIDATED", "KILLED", "PARKED"}),
    "VALIDATED": frozenset(),
    "KILLED": frozenset(),
}


def validate_transition(from_status: str, to_status: str) -> None:
    if from_status not in VALID_TRANSITIONS:
        raise ValueError(f"Unknown source status: {from_status}")
    if to_status not in VALID_TRANSITIONS[from_status]:
        raise ValueError(f"Invalid transition: {from_status} -> {to_status}")
