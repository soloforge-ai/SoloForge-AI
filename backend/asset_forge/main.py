from __future__ import annotations

import base64
import io
import math
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw


app = FastAPI(title="SoloForge Asset Forge API", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHARACTER_REFERENCE_DIR = Path(__file__).resolve().parent / "characters"
CHARACTER_LIBRARY_BASE_URL = (
    "https://raw.githubusercontent.com/soloforge-ai/SoloForge-AI/main/"
    "frontend/assets/characters"
)


class AssetForgeRequest(BaseModel):
    character: str = Field(default="Pearli", min_length=1, max_length=80)
    product: str = Field(default="Sticker", min_length=1, max_length=80)
    theme: str = Field(default="Healing & Encouragement", min_length=1, max_length=120)
    style: str = Field(default="Cute 3D Chibi", min_length=1, max_length=120)
    quantity: int = Field(default=12, ge=4, le=24)
    messages: List[str] = Field(default_factory=list, max_length=24)


class AssetForgeResponse(BaseModel):
    asset_pack_name: str
    files: List[str]
    zip_base64: str
    source_image_base64: str


def _grid(quantity: int) -> tuple[int, int]:
    columns = min(6, max(2, math.ceil(math.sqrt(quantity))))
    rows = math.ceil(quantity / columns)
    return columns, rows


def _character_key(character: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in character).strip("_")


def _load_character_reference(character: str) -> bytes | None:
    """Load a character master from the backend first, then SoloForge's library."""
    key = _character_key(character)
    reference_dir = CHARACTER_REFERENCE_DIR / key

    for filename in ("master.png", "master.jpg", "master.jpeg", "reference.png", "reference.jpg"):
        path = reference_dir / filename
        if path.exists() and path.is_file():
            return path.read_bytes()

    for filename in ("master.png", "master.jpg", "master.jpeg"):
        url = f"{CHARACTER_LIBRARY_BASE_URL}/{key}/references/{filename}"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                data = response.read()
            if data:
                return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue

    return None


def _build_prompt(request: AssetForgeRequest, columns: int, rows: int, has_reference: bool) -> str:
    reference_instruction = """
CHARACTER REFERENCE:
- A master reference image of the character is available in the character library.
- Treat that image as the authoritative character design.
- Preserve the same face, hairstyle, eye colors, skin tone, costume, wings, halo, jewelry, proportions, and signature accessories.
- Do not redesign, age, simplify, or substitute the character.
- Only change pose, facial expression, and gesture as needed for the sticker pack.
""" if has_reference else """
CHARACTER REFERENCE:
- No master reference image is currently available.
- Use the character name and style direction only.
"""

    message_block = "\n".join(
        f"{index + 1}. {message.strip()}"
        for index, message in enumerate(request.messages)
        if message.strip()
    ) or "No specific sticker messages were supplied. Create distinct expressive poses."

    return f"""
Create a commercial-quality sticker sheet for the character {request.character}.
Theme: {request.theme}.
Visual style: {request.style}.
Product: {request.product}.
{reference_instruction}

STICKER MESSAGE INTENT:
The app will add the exact Thai text later. Do NOT render text, letters, captions, speech bubbles, logos, or watermarks in the artwork.
Use these messages only to determine the matching emotion, facial expression, pose, and gesture:
{message_block}

IMPORTANT LAYOUT:
- Create exactly {request.quantity} separate sticker poses in a clean {columns} columns x {rows} rows grid.
- Each pose must be fully visible, centered inside its own equal-sized cell.
- Keep generous empty space between cells so every sticker can be cropped independently.
- Use a simple light/white background so background removal is easy.
- Keep the character design highly consistent across every cell.
- Do not add borders, frames, grid lines, logos, watermarks, or extra characters.
- Do not put written words or captions inside the artwork. The app will add text later.
- Make every pose expressive and clearly different.
- Square 1:1 composition.

Character direction: {request.character} should look cute, friendly, polished and suitable for a commercial digital sticker pack.
""".strip()


def _generate_sheet(prompt: str, reference_bytes: bytes | None) -> bytes:
    """Generate one image sheet through Pollinations."""
    api_key = os.getenv("POLLINATIONS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="POLLINATIONS_API_KEY is not configured on the Asset Forge server.")

    model = os.getenv("POLLINATIONS_IMAGE_MODEL", "flux").strip() or "flux"
    width = int(os.getenv("POLLINATIONS_IMAGE_WIDTH", "1024"))
    height = int(os.getenv("POLLINATIONS_IMAGE_HEIGHT", "1024"))

    # MVP uses text-to-image only. Reference-image generation will be added after
    # the low-memory end-to-end pipeline is stable.
    del reference_bytes

    query = urllib.parse.urlencode({"model": model, "width": width, "height": height})
    url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt, safe='')}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/png,image/jpeg;q=0.9,*/*;q=0.8",
            "User-Agent": "SoloForge-Asset-Forge/0.6",
        },
        method="GET",
    )

    timeout_seconds = int(os.getenv("POLLINATIONS_TIMEOUT_SECONDS", "240"))
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Pollinations image generation failed ({exc.code}): {body[:1200]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail=f"Pollinations image generation timed out or could not connect: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pollinations image generation failed: {str(exc)[:1200]}") from exc

    if not data:
        raise HTTPException(status_code=502, detail="Pollinations returned an empty image response.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pollinations returned data that is not a valid image: {exc}") from exc

    return data


def _remove_simple_background(image: Image.Image, threshold: int = 48) -> Image.Image:
    """Low-memory removal for flat/light backgrounds on generated sticker cells."""
    rgba = image.convert("RGBA")
    transparent = (255, 255, 255, 0)
    draw = ImageDraw.Draw(rgba)
    corners = [
        (0, 0),
        (rgba.width - 1, 0),
        (0, rgba.height - 1),
        (rgba.width - 1, rgba.height - 1),
    ]
    for point in corners:
        draw.floodfill(rgba, point, transparent, thresh=threshold)
    return rgba


def _process_sheet(source_bytes: bytes, request: AssetForgeRequest) -> tuple[list[tuple[str, bytes]], bytes]:
    columns, rows = _grid(request.quantity)
    source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    cell_width = source.width // columns
    cell_height = source.height // rows

    files: list[tuple[str, bytes]] = []
    for index in range(request.quantity):
        row = index // columns
        column = index % columns
        left = column * cell_width
        top = row * cell_height
        right = source.width if column == columns - 1 else (column + 1) * cell_width
        bottom = source.height if row == rows - 1 else (row + 1) * cell_height

        crop = source.crop((left, top, right, bottom))
        processed = _remove_simple_background(crop)

        alpha = processed.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            processed = processed.crop(bbox)

        margin = max(8, min(processed.size) // 20)
        canvas = Image.new(
            "RGBA",
            (processed.width + margin * 2, processed.height + margin * 2),
            (255, 255, 255, 0),
        )
        canvas.alpha_composite(processed, (margin, margin))

        filename = f"{index + 1:02d}_{request.character.lower()}_sticker.png"
        output = io.BytesIO()
        canvas.save(output, format="PNG", optimize=True)
        files.append((filename, output.getvalue()))

    return files, source_bytes


def _zip_files(files: list[tuple[str, bytes]], request: AssetForgeRequest) -> bytes:
    pack_name = f"{request.character}_{request.product}_{request.quantity}pack".replace(" ", "_")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, data in files:
            archive.writestr(f"{pack_name}/{filename}", data)
    return output.getvalue()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "asset-forge"}


@app.post("/v1/asset-forge/generate", response_model=AssetForgeResponse)
def generate_asset_pack(request: AssetForgeRequest) -> AssetForgeResponse:
    try:
        reference_bytes = _load_character_reference(request.character)
        if _character_key(request.character) == "pearli" and reference_bytes is None:
            raise HTTPException(status_code=409, detail="Pearli master reference is missing from the SoloForge character library.")

        columns, rows = _grid(request.quantity)
        prompt = _build_prompt(request, columns, rows, reference_bytes is not None)
        source_bytes = _generate_sheet(prompt, reference_bytes)
        files, source_bytes = _process_sheet(source_bytes, request)
        zip_bytes = _zip_files(files, request)

        pack_name = f"{request.character}_{request.product}_{request.quantity}pack".replace(" ", "_")
        return AssetForgeResponse(
            asset_pack_name=pack_name,
            files=[name for name, _ in files],
            zip_base64=base64.b64encode(zip_bytes).decode("ascii"),
            source_image_base64=base64.b64encode(source_bytes).decode("ascii"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        error_text = str(exc).strip() or exc.__class__.__name__
        raise HTTPException(status_code=500, detail=f"Asset Forge processing failed: {error_text[:1200]}") from exc
