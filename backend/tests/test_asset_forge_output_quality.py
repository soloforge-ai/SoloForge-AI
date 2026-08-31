from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from backend.asset_forge.backend.output_quality import (
    COLORED_CHARACTER_CLEANUP_THRESHOLD,
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


def test_red_dog_fixture_removes_reachable_white_floor_without_hollowing_details() -> None:
    fixture = Path(__file__).parent / "fixtures" / "red_dog_original_sheet.png.b64"
    request = _Request(quantity=4, character="Red Dog chibi mascot")

    files, _ = process_sheet(base64.b64decode(fixture.read_text()), request)

    assert len(files) == 4
    retained_neutral_highlights = 0
    for filename, data in files:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        alpha = image.getchannel("A")
        assert alpha.getbbox() is not None, filename

        # Any nearly-white matte still touching transparency is background,
        # not an enclosed eye highlight or collar tag.
        pixels = image.load()
        matte_pixels = 0
        for y in range(image.height):
            for x in range(image.width):
                r, g, b, a = pixels[x, y]
                if a < 32 or min(r, g, b) < 180 or max(r, g, b) - min(r, g, b) > 18:
                    continue
                retained_neutral_highlights += 1
                if any(
                    0 <= nx < image.width
                    and 0 <= ny < image.height
                    and pixels[nx, ny][3] == 0
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                ):
                    matte_pixels += 1

        assert matte_pixels == 0, f"{filename} retained {matte_pixels} reachable matte pixels"

    # The old strict-only flood retained roughly 5,000 light matte pixels in
    # this fixture. The lower bound protects the enclosed eye/tag highlights.
    assert 600 <= retained_neutral_highlights < 1500


def test_white_primary_color_disables_cleanup_even_with_red_accent() -> None:
    source = _make_white_suit_crop()
    request = _Request(quantity=4, character="White dog with red collar")

    # Build a four-cell sheet from the same near-white foreground contract.
    sheet = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
    for left, top in ((0, 0), (128, 0), (0, 128), (128, 128)):
        sheet.alpha_composite(source.resize((128, 128)), (left, top))
    output = io.BytesIO()
    sheet.save(output, format="PNG")

    files, _ = process_sheet(output.getvalue(), request)

    for filename, data in files:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        alpha = image.getchannel("A")
        assert alpha.getbbox() is not None, filename
        assert sum(value >= 200 for value in alpha.getdata()) > 1000, filename


def test_colored_character_cleanup_preserves_white_silhouette_detail_core() -> None:
    crop = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    draw = ImageDraw.Draw(crop)
    draw.ellipse((28, 24, 100, 108), fill=(220, 30, 35, 255))
    # A legitimate white tail tip/paw reaches the outer silhouette.
    draw.ellipse((84, 54, 122, 88), fill=(245, 243, 240, 255))

    processed = remove_background_soft(
        crop,
        cleanup_threshold=COLORED_CHARACTER_CLEANUP_THRESHOLD,
        blur_radius=0,
    )

    # The cleanup may remove a narrow matte-facing edge, but must not flood
    # through and erase the entire connected white foreground detail.
    assert processed.getpixel((100, 71))[3] == 255
    assert processed.getpixel((108, 71))[3] == 255


def test_colored_character_cleanup_removes_warm_ground_shadow_under_feet() -> None:
    crop = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    draw = ImageDraw.Draw(crop)
    # A red body and two feet partially enclose a warm grey generated shadow.
    draw.ellipse((30, 18, 98, 104), fill=(220, 30, 35, 255))
    draw.ellipse((22, 88, 62, 119), fill=(220, 30, 35, 255))
    draw.ellipse((66, 88, 106, 119), fill=(220, 30, 35, 255))
    draw.ellipse((45, 104, 83, 121), fill=(176, 166, 160, 255))

    processed = remove_background_soft(
        crop,
        cleanup_threshold=COLORED_CHARACTER_CLEANUP_THRESHOLD,
        blur_radius=0,
    )

    assert processed.getpixel((64, 116))[3] == 0
    assert processed.getpixel((64, 110))[3] == 0
    assert processed.getpixel((42, 106))[3] == 255


def test_ground_cleanup_preserves_white_paw_in_lower_region() -> None:
    crop = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    draw = ImageDraw.Draw(crop)
    draw.ellipse((28, 20, 100, 108), fill=(220, 30, 35, 255))
    # This exposed white paw sits wholly inside the deeper ground-cleanup band.
    draw.ellipse((82, 92, 124, 126), fill=(245, 243, 240, 255))

    processed = remove_background_soft(
        crop,
        cleanup_threshold=COLORED_CHARACTER_CLEANUP_THRESHOLD,
        blur_radius=0,
    )

    assert processed.getpixel((101, 108))[3] == 255
    assert processed.getpixel((108, 108))[3] == 255


def test_red_dog_cleanup_scales_to_default_production_sheet_size() -> None:
    fixture = Path(__file__).parent / "fixtures" / "red_dog_original_sheet.png.b64"
    source = Image.open(
        io.BytesIO(base64.b64decode(fixture.read_text()))
    ).convert("RGBA")
    production_sheet = source.resize((1024, 1024), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    production_sheet.save(encoded, format="PNG")

    files, _ = process_sheet(
        encoded.getvalue(),
        _Request(quantity=4, character="Red Dog chibi mascot"),
    )

    assert len(files) == 4
    for filename, data in files:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        pixels = image.load()
        reachable_matte = 0
        for y in range(image.height):
            for x in range(image.width):
                r, g, b, a = pixels[x, y]
                if a < 32 or min(r, g, b) < 180 or max(r, g, b) - min(r, g, b) > 18:
                    continue
                if any(
                    0 <= nx < image.width
                    and 0 <= ny < image.height
                    and pixels[nx, ny][3] == 0
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                ):
                    reachable_matte += 1

        assert reachable_matte == 0, f"{filename} retained {reachable_matte} matte edge pixels"
