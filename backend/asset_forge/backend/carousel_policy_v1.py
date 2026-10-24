"""Offline-only P0 policy preflight for Sales Carousel v1.

Not an authorization server. Approval records must be issued/verified and consumed
atomically by a future authenticated backend before any billable generation call.
No network, tokens, or generation executor in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

QUEST = "quest"
PAID = "paid"
MODEL_CATALOG_V1 = {
    "black-forest-labs/flux.1-schnell": {"wallet": QUEST, "kind": "text_to_image"},
    "black-forest-labs/flux.2-klein-4b": {"wallet": QUEST, "kind": "image_edit"},
    "microsoft/mai-image-2.6-flash": {"wallet": QUEST, "kind": "image_edit"},
    "black-forest-labs/flux.1-kontext-pro": {"wallet": QUEST, "kind": "image_edit"},
    "openai/gpt-image-1.5": {"wallet": QUEST, "kind": "image_edit"},
    "alibaba/wan-2.2-fast": {"wallet": PAID, "kind": "video"},
}
VALID_TASKS = {"draft_scene", "reference_edit", "premium_hero"}
MAX_REQUESTS = 4


class GateError(ValueError):
    pass


def _money(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise GateError("A nonnegative decimal budget is required")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise GateError("Invalid budget") from None
    if not result.is_finite() or result < 0:
        raise GateError("Budget must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class GenerationIntent:
    job_id: str
    model: str
    task: str
    count: int
    max_cost_pollen: str
    product_reference_sha256: str
    storyboard_sha256: str

    def validate(self) -> None:
        if not self.job_id.strip() or len(self.job_id) > 128:
            raise GateError("Job ID required")
        if self.model not in MODEL_CATALOG_V1:
            raise GateError("Unknown model: deny by default")
        if MODEL_CATALOG_V1[self.model]["wallet"] != QUEST:
            raise GateError("Paid models are disabled in v1")
        if self.task not in VALID_TASKS or not isinstance(self.count, int) or isinstance(self.count, bool):
            raise GateError("Invalid task or count")
        if not 1 <= self.count <= MAX_REQUESTS:
            raise GateError("Request count outside approved bounds")
        _money(self.max_cost_pollen)
        for digest in (self.product_reference_sha256, self.storyboard_sha256):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise GateError("SHA256 binding is required")

    def fingerprint(self) -> str:
        self.validate()
        encoded = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()


def preflight(
    intent: GenerationIntent,
    *,
    available_quest_pollen: object,
    estimated_max_pollen: object | None,
    owner_approved_fingerprint: str | None,
    approval_verified: bool = False,
    atomic_claim_confirmed: bool = False,
) -> dict[str, object]:
    """Fail closed until owner approval, trusted price, and atomic claim exist.

    Supplying a fingerprint string alone is NOT authorization.
    """
    intent.validate()
    reasons: list[str] = []
    if owner_approved_fingerprint != intent.fingerprint() or not approval_verified:
        reasons.append("VERIFIED_OWNER_APPROVAL_REQUIRED")
    if not atomic_claim_confirmed:
        reasons.append("ATOMIC_CLAIM_REQUIRED")
    budget = _money(intent.max_cost_pollen)
    available = _money(available_quest_pollen)
    if estimated_max_pollen is None:
        reasons.append("TRUSTED_PRICE_QUOTE_REQUIRED")
    else:
        quote = _money(estimated_max_pollen)
        if quote > budget:
            reasons.append("QUOTE_EXCEEDS_APPROVED_BUDGET")
        if quote > available:
            reasons.append("INSUFFICIENT_QUEST_BALANCE")
    # This version is deliberately only a preflight: never return an executable permit.
    reasons.append("EXECUTOR_DISABLED_V1")
    return {
        "status": "BLOCKED",
        "reasons": reasons,
        "intent_fingerprint": intent.fingerprint(),
        "wallet": QUEST,
        "authorized_requests": 0,
        "auto_retry": False,
        "publish": False,
    }
