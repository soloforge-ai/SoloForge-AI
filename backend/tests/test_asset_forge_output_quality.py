from __future__ import annotations

import io
from dataclasses import dataclass

import pytest
from PIL import Image, ImageDraw

from backend.asset_forge.backend.grid_policy import (
    MAX_SUPPORTED_QUANTITY,
    SUPPORTED_GRID_LAYOUTS,
    exact_grid,
)
from backend.asset_forge.backend.output_quality import (
    OUTPUT_PADDING,
    OUTPUT_SIZE,
    StickerSheetQualityError,
    process_sheet,
    remove_background_soft,
    standardize_sticker,
)


@dataclass
class _Request:
    quantity: int = 4
    character: str = "CEO"


def _make_white_suit_crop() -> Image.Image:
    image = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((34, 10, 94, 70), fill=(28, 25, 26, 255))
    draw.rectangle((42, 56, 86, 113), fill=(249, 247, 245, 255))
    draw.rectangle((54, 58, 74, 104), fill=(28, 25, 26, 255))
    return image


def _make_sheet() -> bytes:
    sheet = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    cells = ((0, 0), (256, 0), (0, 256), (256, 256))
    for index, (left, top) in enumerate(cells):
        inset = 42 + index * 4
        draw.ellipse(
            (left + inset, top + 24, left + 256 - inset, top + 196),
            fill=(24 + index * 8, 28, 32, 255),
        )
        draw.rectangle(
            (left + 82, top + 164, left + 174, top + 234),
            fill=(249, 247, 245, 255),
        )
    output = io.BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue()


def _make_bad_central_hero_sheet() -> bytes:
    """Simulate the Pollinations failure: one large hero crosses the 2x2 split."""
    sheet = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    for cx, cy in ((96, 96), (416, 96), (96, 416), (416, 416)):
        draw.ellipse((cx - 44, cy - 58, cx + 44, cy + 58), fill=(20, 20, 24, 255))

    draw.ellipse((176, 104, 336, 264), fill=(10, 10, 14, 255))
    draw.rounded_rectangle((188, 226, 324, 438), radius=44, fill=(16, 16, 20, 255))

    output = io.BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue()


def _make_two_subjects_in_one_cell_sheet(*, shared_shadow: bool = False) -> bytes:
    """Create duplicate figures; optionally join them only through a thin ground shadow."""
    sheet = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    cells = ((0, 0), (256, 0), (0, 256), (256, 256))

    for index, (left, top) in enumerate(cells):
        if index == 0:
            draw.ellipse((left + 42, top + 64, left + 112, top + 180), fill=(16, 16, 20, 255))
            draw.ellipse((left + 144, top + 64, left + 214, top + 180), fill=(20, 20, 24, 255))
            if shared_shadow:
                draw.rounded_rectangle(
                    (left + 36, top + 176, left + 220, top + 180),
                    radius=2,
                    fill=(24, 24, 28, 255),
                )
        else:
            draw.ellipse((left + 76, top + 46, left + 180, top + 198), fill=(24, 24, 28, 255))

    output = io.BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue()


def test_exact_grid_policy_has_no_unused_cells() -> None:
    assert SUPPORTED_GRID_LAYOUTS == {
        4: (2, 2),
        8: (4, 2),
        12: (4, 3),
        16: (4, 4),
        20: (5, 4),
        24: (6, 4),
    }
    assert MAX_SUPPORTED_QUANTITY == 24
    for quantity, (columns, rows) in SUPPORTED_GRID_LAYOUTS.items():
        assert exact_grid(quantity) == (columns, rows)
        assert columns * rows == quantity


def test_exact_grid_policy_rejects_unsupported_pack_size() -> None:
    with pytest.raises(ValueError, match="Supported pack sizes"):
        exact_grid(6)


def test_soft_background_removal_preserves_white_suit_and_creates_soft_edge() -> None:
    processed = remove_background_soft(_make_white_suit_crop())

    assert processed.getpixel((64, 90))[3] >= 240
    assert processed.getpixel((0, 0))[3] == 0

    alpha_values = set(processed.getchannel("A").getdata())
    assert any(0 < value < 255 for value in alpha_values), (
        "Expected semi-transparent antialiased edge pixels, but alpha remained binary."
    )


def test_defringe_propagates_foreground_rgb_across_full_soft_edge() -> None:
    source = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    draw = ImageDraw.Draw(source)
    draw.rectangle((20, 12, 43, 51), fill=(0, 0, 0, 255))

    processed = remove_background_soft(source)
    alpha = processed.getchannel("A")
    soft_edge_pixels = []
    for y in range(processed.height):
        for x in range(processed.width):
            a = alpha.getpixel((x, y))
            if 0 < a < 255:
                soft_edge_pixels.append(processed.getpixel((x, y)))

    assert soft_edge_pixels, "Expected a non-empty semi-transparent edge."
    assert all(max(pixel[:3]) <= 8 for pixel in soft_edge_pixels), (
        "Semi-transparent edge retained light source-background RGB and can halo on dark surfaces."
    )

    dark = Image.new("RGBA", processed.size, (16, 16, 16, 255))
    composite = Image.alpha_composite(dark, processed)
    for y in range(processed.height):
        for x in range(processed.width):
            a = alpha.getpixel((x, y))
            if 0 < a < 255:
                assert max(composite.getpixel((x, y))[:3]) <= 16


def test_standardize_sticker_outputs_fixed_512_canvas_without_crop() -> None:
    processed = remove_background_soft(_make_white_suit_crop())
    standardized = standardize_sticker(processed)

    assert standardized.mode == "RGBA"
    assert standardized.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    bbox = standardized.getchannel("A").getbbox()
    assert bbox is not None
    left, top, right, bottom = bbox
    assert left >= OUTPUT_PADDING - 4
    assert top >= OUTPUT_PADDING - 4
    assert right <= OUTPUT_SIZE - OUTPUT_PADDING + 4
    assert bottom <= OUTPUT_SIZE - OUTPUT_PADDING + 4


def test_process_sheet_returns_four_standardized_transparent_pngs() -> None:
    files, source = process_sheet(_make_sheet(), _Request())

    assert len(files) == 4
    assert source == _make_sheet()

    for filename, data in files:
        assert filename.endswith("_ceo_sticker.png")
        with Image.open(io.BytesIO(data)) as image:
            rgba = image.convert("RGBA")
            assert rgba.size == (512, 512)
            alpha = rgba.getchannel("A")
            assert alpha.getextrema()[0] == 0
            alpha_values = set(alpha.getdata())
            assert any(0 < value < 255 for value in alpha_values)
            assert alpha.getbbox() is not None


def test_process_sheet_rejects_central_hero_crossing_cell_boundaries() -> None:
    with pytest.raises(StickerSheetQualityError, match="boundary|oversized|clipped"):
        process_sheet(_make_bad_central_hero_sheet(), _Request())


def test_process_sheet_rejects_two_substantial_subjects_in_one_cell() -> None:
    with pytest.raises(StickerSheetQualityError, match="multiple substantial subjects"):
        process_sheet(_make_two_subjects_in_one_cell_sheet(), _Request())


def test_process_sheet_rejects_two_subjects_joined_only_by_shared_shadow() -> None:
    with pytest.raises(StickerSheetQualityError, match="multiple substantial subjects"):
        process_sheet(_make_two_subjects_in_one_cell_sheet(shared_shadow=True), _Request())
