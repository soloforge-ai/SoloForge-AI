from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import textwrap
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont


ASSET_PROVIDER_VERSION = "asset_provider_v0.1"
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1350


def _dimensions() -> tuple[int, int]:
    width = int(os.getenv("CONTENT_ASSET_WIDTH", str(DEFAULT_WIDTH)))
    height = int(os.getenv("CONTENT_ASSET_HEIGHT", str(DEFAULT_HEIGHT)))
    return max(320, width), max(320, height)


def _pollinations_image(prompt: str) -> bytes:
    api_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")

    width, height = _dimensions()
    model = os.getenv("CONTENT_ASSET_MODEL", "flux").strip() or "flux"
    query = urllib.parse.urlencode(
        {
            "model": model,
            "width": width,
            "height": height,
            "nologo": "true",
        }
    )
    url = (
        "https://gen.pollinations.ai/image/"
        f"{urllib.parse.quote(prompt, safe='')}?{query}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/png,image/jpeg;q=0.9,*/*;q=0.8",
            "User-Agent": "SoloForge-Content-Asset/0.2",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Pollinations image HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Pollinations image unavailable") from exc

    if not data:
        raise RuntimeError("Pollinations image returned no bytes")
    return data


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int = 28) -> list[str]:
    compact = " ".join((text or "").split()).strip()
    if not compact:
        return ["SoloForge"]

    words = compact.split(" ")
    if len(words) > 1:
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines[:6]

    return [
        chunk
        for chunk in textwrap.wrap(compact, width=max_chars, break_long_words=True)
        if chunk
    ][:6]


def _template_image(*, title: str, subtitle: str | None = None) -> bytes:
    width, height = _dimensions()
    image = Image.new("RGB", (width, height), (17, 21, 30))
    draw = ImageDraw.Draw(image)

    margin = max(48, width // 14)
    accent_h = max(12, height // 90)
    draw.rounded_rectangle(
        (margin, margin, width - margin, margin + accent_h),
        radius=accent_h // 2,
        fill=(129, 87, 102),
    )

    title_font = _load_font(max(34, width // 18))
    small_font = _load_font(max(22, width // 34))
    brand_font = _load_font(max(20, width // 40))

    title_lines = _wrap_text(title, max_chars=26)
    y = int(height * 0.24)
    line_gap = max(12, height // 90)

    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_h = bbox[3] - bbox[1]
        draw.text(
            (margin, y),
            line,
            font=title_font,
            fill=(244, 240, 233),
        )
        y += line_h + line_gap

    subtitle_text = (subtitle or "").strip()
    if subtitle_text:
        y += max(12, height // 55)
        for line in _wrap_text(subtitle_text, max_chars=36)[:4]:
            bbox = draw.textbbox((0, 0), line, font=small_font)
            line_h = bbox[3] - bbox[1]
            draw.text(
                (margin, y),
                line,
                font=small_font,
                fill=(183, 187, 197),
            )
            y += line_h + max(8, height // 130)

    footer = "AI HACKWORK · SoloForge"
    draw.text(
        (margin, height - margin - max(30, height // 32)),
        footer,
        font=brand_font,
        fill=(154, 157, 170),
    )

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def generate_asset(
    prompt: str,
    *,
    fallback_title: str,
    fallback_subtitle: str | None = None,
) -> tuple[bytes, dict[str, object]]:
    attempts: list[dict[str, str]] = []

    try:
        data = _pollinations_image(prompt)
        return data, {
            "provider": "pollinations",
            "mode": "ai_generated",
            "provider_version": ASSET_PROVIDER_VERSION,
            "attempts": [{"provider": "pollinations", "result": "success"}],
        }
    except Exception as exc:
        attempts.append(
            {
                "provider": "pollinations",
                "result": "failed",
                "error_type": type(exc).__name__,
            }
        )

    data = _template_image(
        title=fallback_title,
        subtitle=fallback_subtitle,
    )
    attempts.append({"provider": "local_template", "result": "success"})
    return data, {
        "provider": "local_template",
        "mode": "deterministic_fallback",
        "provider_version": ASSET_PROVIDER_VERSION,
        "attempts": attempts,
    }
