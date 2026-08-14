from __future__ import annotations

import base64
import io
import math
import os
import zipfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image
from rembg import remove
from google import genai
from google.genai import types


app = FastAPI(title="SoloForge Asset Forge API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


CHARACTER_REFERENCE_DIR = Path(__file__).resolve().parent / "characters"


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
    key = _character_key(character)
    reference_dir = CHARACTER_REFERENCE_DIR / key

    for filename in ("master.png", "master.jpg", "master.jpeg", "reference.png", "reference.jpg"):
        path = reference_dir / filename
        if path.exists() and path.is_file():
            return path.read_bytes()

    return None


def _build_prompt(request: AssetForgeRequest, columns: int, rows: int, has_reference: bool) -> str:
    reference_instruction = """
CHARACTER REFERENCE:
- A master reference image of the character is provided with this request.
- Treat that image as the authoritative character design.
- Preserve the same face, hairstyle, eye colors, skin tone, costume, wings, halo, jewelry, proportions, and signature accessories.
- Do not redesign, age, simplify, or substitute the character.
- Only change pose, facial expression, and gesture as needed for the sticker pack.
""" if has_reference else """
CHARACTER REFERENCE:
- No master reference image is currently available.
- Use the character name and style direction only.
"""

    return f"""
Create a commercial-quality sticker sheet for the character {request.character}.
Theme: {request.theme}.
Visual style: {request.style}.
Product: {request.product}.
{reference_instruction}

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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured on the Asset Forge server.")

    client = genai.Client(api_key=api_key)
    contents: list[object] = []

    if reference_bytes is not None:
        contents.append(types.Part.from_bytes(data=reference_bytes, mime_type="image/png"))

    contents.append(prompt)

    response = client.models.generate_content(
        model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            response_format={"image": {"aspect_ratio": "1:1", "image_size": "1K"}},
        ),
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

    raise HTTPException(status_code=502, detail="Gemini did not return an image.")


def _process_sheet(source_bytes: bytes, request: AssetForgeRequest) -> tuple[list[tuple[str, bytes]], bytes]:
    columns, rows = _grid(request.quantity)
    source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    cell_width = source.width // columns
    cell_height = source.height // rows

    messages = [m.strip() for m in request.messages if m.strip()]
    files: list[tuple[str, bytes]] = []

    for index in range(request.quantity):
        row = index // columns
        column = index % columns
        left = column * cell_width
        top = row * cell_height
        right = source.width if column == columns - 1 else (column + 1) * cell_width
        bottom = source.height if row == rows - 1 else (row + 1) * cell_height

        crop = source.crop((left, top, right, bottom))
        processed = remove(crop)

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
    reference_bytes = _load_character_reference(request.character)

    # Pearli must use the locked master reference. This prevents accidental generation
    # of a visually different Pearli before the character library is configured.
    if _character_key(request.character) == "pearli" and reference_bytes is None:
        raise HTTPException(
            status_code=409,
            detail="Pearli master reference is missing. Upload backend/asset_forge/characters/pearli/master.png before generating assets.",
        )

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
