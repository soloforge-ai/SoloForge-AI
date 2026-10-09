from __future__ import annotations

import pytest

from backend.asset_forge.backend.carousel_policy_v1 import (
    GateError, GenerationIntent, preflight,
)
from backend.asset_forge.backend.sales_carousel_skill_v1 import plan_sales_carousel


def intent(model="microsoft/mai-image-2.6-flash", count=1):
    return GenerationIntent("ouku-pilot-001", model, "reference_edit", count, "0.30", "a" * 64, "b" * 64)


def test_preflight_denies_without_approval_and_claim():
    result = preflight(intent(), available_quest_pollen="17.53", estimated_max_pollen="0.02", owner_approved_fingerprint=None)
    assert result["status"] == "BLOCKED"
    assert result["authorized_requests"] == 0
    assert "VERIFIED_OWNER_APPROVAL_REQUIRED" in result["reasons"]
    assert "ATOMIC_CLAIM_REQUIRED" in result["reasons"]


def test_even_all_approval_flags_cannot_execute_v1():
    entry = intent()
    result = preflight(entry, available_quest_pollen="17.53", estimated_max_pollen="0.02",
        owner_approved_fingerprint=entry.fingerprint(), approval_verified=True, atomic_claim_confirmed=True)
    assert result["reasons"] == ["EXECUTOR_DISABLED_V1"]


@pytest.mark.parametrize("model", ["alibaba/wan-2.2-fast", "unlisted-model"])
def test_paid_or_unknown_denied(model):
    with pytest.raises(GateError):
        preflight(intent(model=model), available_quest_pollen=50, estimated_max_pollen="0.02", owner_approved_fingerprint=None)


def test_budget_and_balance_denied():
    result = preflight(intent(), available_quest_pollen="0.01", estimated_max_pollen="0.35", owner_approved_fingerprint=None)
    assert "INSUFFICIENT_QUEST_BALANCE" in result["reasons"]
    assert "QUOTE_EXCEEDS_APPROVED_BUDGET" in result["reasons"]


def test_missing_quote_denied():
    result = preflight(intent(), available_quest_pollen="17.53", estimated_max_pollen=None, owner_approved_fingerprint=None)
    assert "TRUSTED_PRICE_QUOTE_REQUIRED" in result["reasons"]


def test_approval_binding_changes_with_count():
    assert intent(count=1).fingerprint() != intent(count=2).fingerprint()


def test_carousel_is_four_slides_review_only():
    result = plan_sales_carousel(product_name="OUKU OK02", reference_assets=[{"sha256": "a" * 64, "role": "hero"}])
    assert [s["role"] for s in result["slides"]] == ["HERO", "FEATURES", "USAGE", "CTA"]
    assert all(s["canvas"] == {"width": 1080, "height": 1350, "ratio": "4:5"} for s in result["slides"])
    assert all(s["review_status"] == "NEEDS_REVIEW" for s in result["slides"])
    assert result["publish_authorized"] is False


def test_carousel_requires_grounded_reference():
    with pytest.raises(ValueError):
        plan_sales_carousel(product_name="OUKU OK02", reference_assets=[])
