from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os

from PIL import Image, ImageDraw, ImageFont


BRAND_STAMP_VERSION = "soloforge_brand_v1"
BRAND_TEXT = "SoloForge AI"


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf",
    ]
    for root in (Path("/usr/share/fonts"), Path("/usr/local/share/fonts")):
        if root.exists():
            candidates.extend(str(path) for path in root.rglob("NotoSansThai*.ttf"))
    candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def stamp_image_bytes(
    data: bytes,
    *,
    preserve_alpha: bool = False,
) -> tuple[bytes, dict[str, object]]:
    image = Image.open(BytesIO(data)).convert("RGBA")
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(18, int(width * 0.028))
    padding_x = max(18, int(width * 0.024))
    padding_y = max(14, int(height * 0.014))
    radius = max(10, int(font_size * 0.45))
    font = _load_font(font_size)

    bbox = draw.textbbox((0, 0), BRAND_TEXT, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    box_w = text_w + padding_x * 2
    box_h = text_h + padding_y * 2
    margin = max(22, int(width * 0.028))
    x1 = width - margin - box_w
    y1 = height - margin - box_h
    x2 = width - margin
    y2 = height - margin

    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=radius,
        fill=(10, 12, 18, 150),
    )
    draw.text(
        (x1 + padding_x, y1 + padding_y - bbox[1]),
        BRAND_TEXT,
        font=font,
        fill=(255, 255, 255, 210),
    )

    branded = Image.alpha_composite(image, overlay)
    if not preserve_alpha:
        branded = branded.convert("RGB")
    output = BytesIO()
    branded.save(output, format="PNG", optimize=True)
    return output.getvalue(), {
        "brand_applied": True,
        "brand_text": BRAND_TEXT,
        "brand_stamp_version": BRAND_STAMP_VERSION,
        "brand_position": "bottom_right",
        "brand_visibility": "subtle",
    }


def ffmpeg_brand_filter() -> str:
    text = BRAND_TEXT.replace("'", "\\'")
    font_size = int(os.getenv("SOLOFORGE_VIDEO_BRAND_FONT_SIZE", "24"))
    return (
        "drawtext="
        f"text='{text}':"
        "fontcolor=white@0.72:"
        f"fontsize={font_size}:"
        "box=1:boxcolor=black@0.38:boxborderw=10:"
        "x=w-tw-28:y=h-th-28"
    )


def provenance_metadata() -> dict[str, object]:
    return {
        "generated_by": "soloforge_ai",
        "brand_text": BRAND_TEXT,
        "brand_stamp_version": BRAND_STAMP_VERSION,
    }
