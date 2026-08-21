from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from backend.asset_forge.main import _remove_simple_background


FIXTURE_B64 = Path(__file__).parent / "fixtures" / "ceo_original_sheet_regression.jpg.b64"

# Protected points sampled from the CEO's white suit in each 2x2 cell.
# The fixture is a reduced copy of the real Pollinations original_sheet.png
# generated during A4 validation. These points must remain opaque after
# background removal; otherwise the white suit is being mistaken for the
# light background.
PROTECTED_POINTS = {
    "happy": (23, 25),
    "hug": (14, 25),
    "sad": (25, 32),
    "laugh": (15, 19),
}


def _load_fixture() -> Image.Image:
    encoded = FIXTURE_B64.read_text(encoding="ascii").strip()
    raw = base64.b64decode(encoded)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def test_white_suit_survives_background_removal() -> None:
    sheet = _load_fixture()
    assert sheet.size == (128, 128)

    cell_width = sheet.width // 2
    cell_height = sheet.height // 2

    failures: list[str] = []

    for index, (pose, point) in enumerate(PROTECTED_POINTS.items()):
        row = index // 2
        column = index % 2
        crop = sheet.crop(
            (
                column * cell_width,
                row * cell_height,
                (column + 1) * cell_width,
                (row + 1) * cell_height,
            )
        )

        x, y = point
        source_rgb = crop.getpixel((x, y))[:3]
        assert min(source_rgb) >= 235, (
            f"Regression fixture point for {pose} is no longer a light suit pixel: "
            f"rgb={source_rgb} at {(x, y)}"
        )

        processed = _remove_simple_background(crop)
        alpha = processed.getpixel((x, y))[3]
        if alpha < 200:
            failures.append(f"{pose}: alpha={alpha} at {(x, y)}")

    assert not failures, (
        "Background removal erased protected white-suit pixels: "
        + "; ".join(failures)
    )
