"""Deterministic, non-billable four-slide storyboard planner.

Separate from the legacy five-slide brand template and short-video skill.
Produces a review-only package, never invokes a model or publishing endpoint.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

SKILL_ID = "SALES_CAROUSEL_4_V1"
SLIDES = ("HERO", "FEATURES", "USAGE", "CTA")
WIDTH, HEIGHT = 1080, 1350
ASH = {
    "obsidian": "#0D0C0F",
    "black_plum": "#17131A",
    "deep_indigo": "#28345C",
    "oxblood": "#541C2A",
    "bone_white": "#E9E3DA",
}


def plan_sales_carousel(
    *,
    product_name: str,
    reference_assets: list[dict[str, str]],
    approved_claims: list[str] | None = None,
    cta: str = "ดูรายละเอียดสินค้า",
) -> dict[str, Any]:
    name = product_name.strip()
    if not name or len(name) > 180:
        raise ValueError("product_name is required (max 180 chars)")
    if not 1 <= len(reference_assets) <= 12:
        raise ValueError("1..12 reference assets required")
    refs = []
    for item in reference_assets:
        digest = str(item.get("sha256", ""))
        role = str(item.get("role", "unassigned")).lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("each reference needs lowercase SHA256")
        if role not in {"hero", "feature", "usage", "detail", "unassigned"}:
            raise ValueError("unknown reference role")
        refs.append({"sha256": digest, "role": role})
    claims = [c.strip() for c in (approved_claims or []) if c.strip()]
    if len(claims) > 4 or any(len(c) > 140 for c in claims):
        raise ValueError("approved claims capped at four short strings")
    if not cta.strip() or len(cta) > 90:
        raise ValueError("CTA required")
    layouts = [
        {"role": "HERO", "headline": name, "ceo": "OPTIONAL_CANON_REFERENCE_REQUIRED"},
        {"role": "FEATURES", "headline": "ดูรายละเอียดสินค้า", "ceo": "OMIT"},
        {"role": "USAGE", "headline": "ตัวอย่างการใช้งาน", "ceo": "OMIT"},
        {"role": "CTA", "headline": cta.strip(), "ceo": "OMIT"},
    ]
    for slide in layouts:
        slide.update({
            "canvas": {"width": WIDTH, "height": HEIGHT, "ratio": "4:5"},
            "source_assets": deepcopy(refs),
            "copy_layer": "NATIVE_THAI_RENDERER",
            "image_generation": "REQUIRES_SEPARATE_APPROVAL",
            "review_status": "NEEDS_REVIEW",
        })
    package = {
        "skill_id": SKILL_ID,
        "version": "1.0",
        "product_name": name,
        "palette": dict(ASH),
        "verified_claims_input": claims,
        "claims_verification": "HUMAN_REQUIRED",
        "rights_verification": "HUMAN_REQUIRED",
        "product_fidelity": "HUMAN_REQUIRED",
        "publish_authorized": False,
        "slides": layouts,
    }
    encoded = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    package["storyboard_sha256"] = sha256(encoded.encode("utf-8")).hexdigest()
    return package
