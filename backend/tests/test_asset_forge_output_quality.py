from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw

from backend.asset_forge.backend.output_quality import (
    OUTPUT_PADDING,
    OUTPUT_SIZE,
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


def test_soft_background_removal_preserves_white_suit_and_creates_soft_edge() -> None:
    processed = remove_background_soft(_make_white_suit_crop())

    assert processed.getpixel((64, 90))[3] >= 240
    assert processed.getpixel((0, 0))[3] == 0

    alpha_values = set(processed.getchannel("A").getdata())
    assert any(0 < value < 255 for value in alpha_values), (
        "Expected semi-transparent antialiased edge pixels, but alpha remained binary."
    )


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
