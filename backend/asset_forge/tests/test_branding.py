from __future__ import annotations

from io import BytesIO

from PIL import Image

from backend.asset_forge.backend import branding


def test_stamp_image_bytes_adds_brand_metadata() -> None:
    source = Image.new("RGB", (640, 800), (20, 24, 32))
    raw = BytesIO()
    source.save(raw, format="PNG")

    stamped, meta = branding.stamp_image_bytes(raw.getvalue())

    assert stamped.startswith(b"\x89PNG")
    assert meta["brand_applied"] is True
    assert meta["brand_text"] == "SoloForge AI"
    assert meta["brand_stamp_version"] == branding.BRAND_STAMP_VERSION
    assert meta["brand_position"] == "bottom_right"


def test_ffmpeg_brand_filter_is_visible_but_subtle() -> None:
    value = branding.ffmpeg_brand_filter()

    assert "SoloForge AI" in value
    assert "fontcolor=white@0.72" in value
    assert "boxcolor=black@0.38" in value
    assert "x=w-tw-28:y=h-th-28" in value


def test_provenance_metadata_marks_soloforge_origin() -> None:
    value = branding.provenance_metadata()

    assert value["generated_by"] == "soloforge_ai"
    assert value["brand_text"] == "SoloForge AI"
    assert value["brand_stamp_version"] == branding.BRAND_STAMP_VERSION
