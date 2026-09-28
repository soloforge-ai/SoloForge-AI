from __future__ import annotations

import pytest

from backend.asset_forge.backend.sales_inbox import (
    lead_keyboard,
    parse_addlead,
    score_lead,
)
from backend.asset_forge.backend.sales_sender import _recipient_from_channel


def test_parse_addlead_minimum_fields():
    payload = parse_addlead("/addlead facebook | ACME | ต้องการ dashboard")
    assert payload["source"] == "facebook"
    assert payload["company"] == "ACME"
    assert payload["need"] == "ต้องการ dashboard"


def test_parse_addlead_rejects_short_input():
    with pytest.raises(ValueError):
        parse_addlead("/addlead facebook | ACME")


def test_high_intent_lead_scores_higher():
    high = score_lead("ACME", "ต้องการคนทำ Excel dashboard automation", "manual report", "buyer@acme.com")
    low = score_lead("ACME", "สนใจข้อมูลทั่วไป", "", "")
    assert high > low
    assert high >= 65


def test_keyboard_prepares_new_lead():
    keyboard = lead_keyboard({"id": 7, "status": "QUALIFIED"})
    labels = [item["text"] for row in keyboard["inline_keyboard"] for item in row]
    assert "📩 เตรียมข้อเสนอ" in labels


def test_keyboard_sends_ready_lead():
    keyboard = lead_keyboard({"id": 7, "status": "READY_TO_SEND"})
    labels = [item["text"] for row in keyboard["inline_keyboard"] for item in row]
    assert "📤 ส่งอีเมล" in labels


def test_sender_requires_email_contact():
    assert _recipient_from_channel("buyer@example.com") == "buyer@example.com"
    with pytest.raises(ValueError):
        _recipient_from_channel("facebook dm")
