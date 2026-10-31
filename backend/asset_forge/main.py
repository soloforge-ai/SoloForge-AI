from __future__ import annotations

from backend.execution_policy import explicitly_enabled, require_generation_execution

import asyncio
import base64
import io
import json
import math
import hashlib
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import List, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from PIL import Image, ImageDraw, ImageOps

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
    router as pollinations_oauth_router,
)
from backend.soloforge_session import require_soloforge_session, router as soloforge_session_router
from backend.owner_v2_router import router as owner_v2_router
from backend.branding import stamp_image_bytes
from backend.output_quality import process_single_image
from backend.content_generation import content_worker_loop
from backend.content_router import content_router_loop
from backend.content_asset_generation import content_asset_worker_loop
from backend.audio_generation import audio_worker_loop
from backend.final_render import create_signed_video_url, final_render_worker_loop
from backend.prawtwan_chat import router as prawtwan_chat_router
from backend.content_jobs_api import router as content_jobs_router
from backend.analytics_api import router as analytics_router
from backend.publishing_api import router as publishing_router
from backend.ops_webhook import router as ops_webhook_router
from backend.byop_router import router as byop_router


app = FastAPI(title="SoloForge Asset Forge API", version="0.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pollinations_oauth_router)
app.include_router(soloforge_session_router)
app.include_router(owner_v2_router)
app.include_router(prawtwan_chat_router)
app.include_router(content_jobs_router)
app.include_router(analytics_router)
app.include_router(publishing_router)
app.include_router(ops_webhook_router)
app.include_router(byop_router)

CHARACTER_REFERENCE_DIR = Path(__file__).resolve().parent / "characters"
CHARACTER_LIBRARY_BASE_URL = (
    "https://raw.githubusercontent.com/soloforge-ai/SoloForge-AI/main/"
    "frontend/assets/characters"
)

_SUPPORTED_CHARACTER_COLORS = frozenset(
    {"blue", "black", "white", "pink", "red", "green", "purple", "yellow"}
)

CEO_MASTER_SHA256 = "93b23ba19273940bb00aca822565ce2e8fde50ba8c45a3ff55b2423e3db5d598"
CEO_OUTFITS = {
    "default": "Canonical white/cream luxury suit, black shirt and red tie",
    "creator": "Black creator hoodie or practical dark techwear",
    "fitness": "Appropriate sportswear and athletic shoes",
    "casual": "Comfortable everyday casual outfit",
    "formal_black": "Elegant black formal suit",
}


class AssetForgeRequest(BaseModel):
    character: str = Field(default="CEO", min_length=1, max_length=80)
    product: str = Field(default="Sticker", min_length=1, max_length=80)
    theme: str = Field(default="Healing & Encouragement", min_length=1, max_length=120)
    style: str = Field(default="Cute 3D Chibi", min_length=1, max_length=120)
    quantity: int = Field(default=12, ge=1, le=24)
    messages: List[str] = Field(default_factory=list, max_length=24)
    wardrobe_variant: Literal["default", "creator", "fitness", "casual", "formal_black"] = "default"
    campaign_id: str | None = Field(default=None, max_length=120)
    generation_layout: Literal["sticker_sheet", "single_character"] = "sticker_sheet"
    pose_intent: Literal["presenting", "pointing", "thinking", "standing"] | None = None
    expression: Literal["calm", "subtle_smile", "thoughtful"] | None = None
    framing: Literal["full_figure", "waist_up"] = "full_figure"

    @model_validator(mode="after")
    def validate_generation_layout(self):
        if self.generation_layout == "sticker_sheet":
            if self.quantity < 4:
                raise ValueError("Sticker sheets require quantity 4–24")
            if self.pose_intent is not None or self.expression is not None:
                raise ValueError("Single pose/expression fields require single_character mode")
        else:
            if self.character.strip().lower() != "ceo" or self.quantity != 1:
                raise ValueError("single_character requires CEO and quantity=1")
            if self.pose_intent is None or self.expression is None:
                raise ValueError("Exactly one pose_intent and expression are required")
            if self.messages:
                raise ValueError("Single-character mode rejects messages; use pose_intent and expression")
            compatible = {
                "presenting": {"calm", "subtle_smile"},
                "pointing": {"calm", "subtle_smile"},
                "thinking": {"calm", "thoughtful"},
                "standing": {"calm", "subtle_smile"},
            }
            if self.expression not in compatible[self.pose_intent]:
                raise ValueError("Expression is incompatible with the selected pose")
        return self


class AssetForgeResponse(BaseModel):
    asset_pack_name: str
    files: List[str]
    zip_base64: str
    source_image_base64: str
    generation_mode: str
    generation_layout: Literal["sticker_sheet", "single_character"] = "sticker_sheet"
    output_manifest: dict = Field(default_factory=dict)


def _grid(quantity: int) -> tuple[int, int]:
    columns = min(6, max(2, math.ceil(math.sqrt(quantity))))
    rows = math.ceil(quantity / columns)
    return columns, rows


def _character_key(character: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in character).strip("_")


def _requested_character_color(character: str) -> str | None:
    """Return the explicit builder color without guessing from character identity."""
    for token in character.strip().lower().replace("_", " ").replace("-", " ").split():
        if token in _SUPPORTED_CHARACTER_COLORS:
            return token
    return None


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
    if request.generation_layout == "single_character":
        return _build_single_character_prompt(request, has_reference)
    requested_color = _requested_character_color(request.character)
    color_instruction = f"""
NON-NEGOTIABLE COLOR OVERRIDE:
- The requested primary character color is {requested_color.upper()}.
- Recolor the character's main fur, coat, skin, body, or shell to {requested_color}; this overrides the color shown in the master reference.
- Apply {requested_color} across the full main body surface in every sticker cell, not only to clothing or accessories.
- Do not keep the master reference's original main body color. Small natural facial details and highlights may retain neutral colors.
""" if requested_color else ""

    reference_instruction = """
CHARACTER REFERENCE:
- The attached master reference image is authoritative for the character's face, hairstyle, eye colors, skin tone, costume, proportions, and signature accessories.
- Preserve those core identity features consistently in every cell.
- IMPORTANT: Do NOT preserve or copy any wings, halo, angel features, bird wings, or other fantasy appendages that may appear in the reference image. The SoloForge AI CEO character has NO wings.
- The CEO must always appear as a human-like cute 3D chibi male mascot with no wings and no halo.
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

    no_wings_rule = """
NON-NEGOTIABLE CEO IDENTITY RULE:
- The CEO has NO wings.
- Never generate angel wings, bird wings, feathers attached to the body, a halo, angelic appendages, or fantasy wings.
- Do not infer wings from the reference image.
- If the reference image contains wings, remove them from the generated character while keeping the face, hair, glasses, outfit, and body proportions consistent.
""" if request.character.strip().lower() == "ceo" else ""

    campaign_locked = (
        request.character.strip().lower() == "ceo"
        and (request.campaign_id or "").strip().lower() == "manifest_glow_lab"
    )
    wardrobe_instruction = ""
    if campaign_locked:
        wardrobe_instruction = (
            "MANIFEST GLOW LAB: Keep the canonical white/cream luxury suit, "
            "dark shirt and red tie. Ignore contextual wardrobe overrides."
        )
    elif request.character.strip().lower() == "ceo" and request.wardrobe_variant != "default":
        approved_outfits = CEO_OUTFITS
        wardrobe_instruction = f"""
APPROVED CONTEXTUAL WARDROBE OVERRIDE:
- Outfit: {approved_outfits[request.wardrobe_variant]}.
- Clothing-only variation: preserve the approved face, eye appearance, hair, large black glasses, skin tone, and 3D chibi proportions.
- Default white suit is not mandatory only for this approved variant.
- Never alter gender presentation, identity, or add wings/halo.
"""
        if has_reference:
            reference_instruction = reference_instruction.replace(
                "skin tone, costume, proportions, and signature accessories",
                "skin tone, proportions, and identity-defining accessories",
            ).replace(
                "Only change pose, facial expression, and gesture as needed for the sticker pack.",
                "Only change approved outfit, pose, facial expression, and gesture as needed for the sticker pack.",
            )
        no_wings_rule = no_wings_rule.replace(
            "face, hair, glasses, outfit, and body proportions",
            "face, hair, glasses, and body proportions",
        )

    ceo_expression_lock = """
NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK:
- Default facial expression: calm, composed, straight-faced, mouth closed, and subtly expressive.
- For any smile, use only a tiny, subtle closed-mouth smile. NEVER show teeth or use an open-mouth smile, wide grin, or exaggerated laughing face.
- When the CEO feels happy, pleased, affectionate, excited, or likes something, show a small closed-mouth smile with a soft natural pink blush on both cheeks.
- When shy or bashful, use a gently lowered or sideways gaze, softly rosy cheeks, and a tiny closed-mouth smile.
- Preserve the approved master face shape, facial proportions, hairstyle, and glasses in every expression.
- These rules override scene or sticker-message requests for a toothy smile, open mouth, exaggerated grin, or dramatic facial distortion.
""" if request.character.strip().lower() == "ceo" else ""

    return f"""
Create a commercial-quality sticker sheet for the character {request.character}.
Theme: {request.theme}.
Visual style: {request.style}.
Product: {request.product}.
{reference_instruction}
{color_instruction}
{no_wings_rule}
{wardrobe_instruction}
{ceo_expression_lock}

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


def _build_single_character_prompt(request: AssetForgeRequest, has_reference: bool) -> str:
    if not has_reference:
        raise ValueError("Single CEO generation requires the approved master reference")
    poses = {
        "presenting": "One presenting gesture with an open hand, holding no object",
        "pointing": "One pointing gesture with one hand",
        "thinking": "One thinking pose with one hand gently near the chin",
        "standing": "One composed standing pose with relaxed arms",
    }
    expressions = {
        "calm": "One calm, composed, closed-mouth expression",
        "subtle_smile": "One tiny subtle closed-mouth smile with a soft natural pink blush",
        "thoughtful": "One calm thoughtful expression with a softly lowered gaze and closed mouth",
    }
    campaign_locked = (request.campaign_id or "").strip().lower() == "manifest_glow_lab"
    wardrobe = CEO_OUTFITS["default" if campaign_locked else request.wardrobe_variant]
    campaign = "MANIFEST GLOW LAB: canonical white suit overrides all wardrobe variants." if campaign_locked else ""
    framing = (
        "Full figure from hair to shoes, completely visible, with generous margin around all limbs; no unintended clipping."
        if request.framing == "full_figure" else
        "One waist-up portrait; keep the entire head and requested gesture visible with generous margins."
    )
    return f"""Create exactly one CEO character in exactly one image.
Exactly one pose and exactly one expression. One male premium polished 3D chibi mascot only.
POSE: {poses[request.pose_intent]}
EXPRESSION: {expressions[request.expression]}
Preserve the attached approved master face, eyes, warm skin tone, black hairstyle, large black glasses and head/body proportions.
Glasses are mandatory. No identity replacement, gender swap, beard or mustache.
Calm closed-mouth facial expression lock: NEVER show teeth, open mouth, exaggerated smile or wide grin.
WARDROBE: {wardrobe}. Clothing-only variation; retain all identity features.
{campaign}
COMPOSITION: {framing} One centered subject, square composition, simple light background.
Premium studio lighting, clean polished 3D rendering, sharp facial details and commercial-quality finish.
No duplicate or multiple character instances, grids, panels, collages, character sheets or alternate poses.
No wings, halo, extra characters, text, letters, logos, watermarks or extra objects.
The selected pose and expression are the sole intent; do not invent additional actions or emotions.""".strip()


def _prepare_reference(reference_bytes: bytes) -> bytes:
    """Keep the reference small enough for the 512 MB Render instance."""
    with Image.open(io.BytesIO(reference_bytes)) as image:
        image = image.convert("RGB")
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue()


def _multipart_body(fields: dict[str, str], file_field: str, filename: str, file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----SoloForgeBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])

    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def _extract_image_response(data: bytes, *, allow_url: bool = True) -> bytes:
    """Accept Pollinations OpenAI-compatible JSON responses with URL or base64 image data."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pollinations returned a non-JSON image response: {exc}") from exc

    items = payload.get("data") or []
    if not items:
        raise HTTPException(status_code=502, detail=f"Pollinations returned no image data: {str(payload)[:1000]}")

    item = items[0] or {}
    b64 = item.get("b64_json")
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Pollinations returned invalid base64 image data: {exc}") from exc

    image_url = item.get("url")
    if image_url:
        if not allow_url:
            raise HTTPException(502, "Pilot requires inline image bytes; URL outcome requires reconciliation")
        try:
            with urllib.request.urlopen(image_url, timeout=60) as response:
                return response.read()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Could not download Pollinations generated image: {exc}") from exc

    raise HTTPException(status_code=502, detail=f"Pollinations image response had no url or b64_json: {str(item)[:1000]}")


def _generate_sheet(
    prompt: str,
    reference_bytes: bytes | None,
    access_token: str,
    *,
    settings: dict | None = None,
) -> bytes:
    """Generate one image sheet through Pollinations using the connected user's token."""
    require_generation_execution()
    model = settings["model"] if settings is not None else (os.getenv("POLLINATIONS_IMAGE_EDIT_MODEL", "kontext").strip() or "kontext")
    width = settings["width"] if settings is not None else int(os.getenv("POLLINATIONS_IMAGE_WIDTH", "1024"))
    height = settings["height"] if settings is not None else int(os.getenv("POLLINATIONS_IMAGE_HEIGHT", "1024"))
    timeout_seconds = int(os.getenv("POLLINATIONS_TIMEOUT_SECONDS", "240"))

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "SoloForge-Asset-Forge/0.8",
    }

    try:
        if reference_bytes is not None:
            compact_reference = _prepare_reference(reference_bytes)
            body, boundary = _multipart_body(
                {
                    "prompt": prompt,
                    "model": model,
                    "size": f"{width}x{height}",
                },
                "image",
                "character-reference.jpg",
                compact_reference,
                "image/jpeg",
            )
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            request = urllib.request.Request(
                "https://gen.pollinations.ai/v1/images/edits",
                data=body,
                headers=headers,
                method="POST",
            )
        else:
            query = urllib.parse.urlencode({"model": "flux", "width": width, "height": height})
            url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt, safe='')}?{query}"
            headers["Accept"] = "image/png,image/jpeg;q=0.9,*/*;q=0.8"
            request = urllib.request.Request(url, headers=headers, method="GET")

        from backend.byop_pilot import active, claim_request
        pilot = active()
        claim_request(prompt, reference_bytes, access_token, {"model": model, "width": width, "height": height})
        if pilot:
            # Never forward the selected credential through a provider redirect.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            open_request = urllib.request.build_opener(NoRedirect()).open
        else:
            open_request = urllib.request.urlopen
        with open_request(request, timeout=timeout_seconds) as response:
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

    if reference_bytes is not None:
        data = _extract_image_response(data, allow_url=not pilot)

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pollinations returned data that is not a valid image: {exc}") from exc

    return data



def _generate_local_fallback_sheet(
    request: AssetForgeRequest,
    reference_bytes: bytes | None,
) -> bytes:
    """Create a deterministic sticker sheet without an external AI call."""
    columns, rows = _grid(request.quantity)
    size = 1024
    sheet = Image.new("RGBA", (size, size), (248, 248, 248, 255))
    draw = ImageDraw.Draw(sheet)
    cell_w = size // columns
    cell_h = size // rows
    accent = {
        "blue": (74, 109, 205, 255),
        "black": (48, 50, 56, 255),
        "white": (225, 226, 230, 255),
        "pink": (211, 112, 157, 255),
        "red": (190, 72, 83, 255),
        "green": (80, 154, 117, 255),
        "purple": (129, 92, 173, 255),
        "yellow": (217, 174, 67, 255),
    }.get(_requested_character_color(request.character) or "blue", (74, 109, 205, 255))

    master = None
    if reference_bytes:
        try:
            master = Image.open(io.BytesIO(reference_bytes)).convert("RGBA")
        except Exception:
            master = None

    for index in range(request.quantity):
        row = index // columns
        col = index % columns
        x0 = col * cell_w
        y0 = row * cell_h
        x1 = size if col == columns - 1 else (col + 1) * cell_w
        y1 = size if row == rows - 1 else (row + 1) * cell_h
        margin = max(18, min(cell_w, cell_h) // 10)
        draw.rounded_rectangle(
            (x0 + margin // 2, y0 + margin // 2, x1 - margin // 2, y1 - margin // 2),
            radius=max(18, margin),
            fill=(255, 255, 255, 255),
        )

        if master is not None:
            tile = master.copy()
            tile.thumbnail((cell_w - margin * 2, cell_h - margin * 2), Image.Resampling.LANCZOS)
            if index % 2 == 1:
                tile = ImageOps.mirror(tile)
            sheet.alpha_composite(
                tile,
                (x0 + (cell_w - tile.width) // 2, y0 + (cell_h - tile.height) // 2),
            )
        else:
            cx = x0 + cell_w // 2
            cy = y0 + cell_h // 2
            head_r = max(24, min(cell_w, cell_h) // 8)
            body_w = head_r * 2
            body_h = int(head_r * 2.4)
            draw.ellipse(
                (cx - head_r, cy - head_r * 2, cx + head_r, cy),
                fill=accent,
            )
            draw.rounded_rectangle(
                (cx - body_w // 2, cy - 2, cx + body_w // 2, cy + body_h),
                radius=head_r,
                fill=accent,
            )
            eye_r = max(2, head_r // 10)
            draw.ellipse(
                (cx - head_r // 3 - eye_r, cy - head_r - eye_r,
                 cx - head_r // 3 + eye_r, cy - head_r + eye_r),
                fill=(20, 20, 24, 255),
            )
            draw.ellipse(
                (cx + head_r // 3 - eye_r, cy - head_r - eye_r,
                 cx + head_r // 3 + eye_r, cy - head_r + eye_r),
                fill=(20, 20, 24, 255),
            )
            arm_y = cy + body_h // 3
            swing = (index % 4 - 1) * max(6, head_r // 3)
            draw.line(
                (cx - body_w // 2, arm_y, cx - body_w, arm_y - swing),
                fill=accent,
                width=max(6, head_r // 4),
            )
            draw.line(
                (cx + body_w // 2, arm_y, cx + body_w, arm_y + swing),
                fill=accent,
                width=max(6, head_r // 4),
            )

    output = io.BytesIO()
    sheet.convert("RGB").save(output, format="PNG", optimize=True)
    branded, _ = stamp_image_bytes(output.getvalue())
    return branded


def _remove_simple_background(
    image: Image.Image,
    threshold: int = 8,
) -> Image.Image:
    """
    Remove only background pixels connected to the outer border.

    Keep the tolerance intentionally strict so near-white foreground details
    (for example the CEO's white suit) are not flooded away with a white
    background. The generated sheets use a simple light background, so an
    8-level RGB tolerance is sufficient while preserving off-white clothing.
    """
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size

    if width == 0 or height == 0:
        return rgba

    sample_points = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ]

    samples = [pixels[x, y][:3] for x, y in sample_points]
    bg_r = sum(c[0] for c in samples) // len(samples)
    bg_g = sum(c[1] for c in samples) // len(samples)
    bg_b = sum(c[2] for c in samples) // len(samples)

    def is_background(x: int, y: int) -> bool:
        r, g, b, _ = pixels[x, y]

        distance = max(
            abs(r - bg_r),
            abs(g - bg_g),
            abs(b - bg_b),
        )

        return distance <= threshold

    visited = bytearray(width * height)
    stack: list[tuple[int, int]] = []

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if visited[index]:
            return
        if not is_background(x, y):
            return

        visited[index] = 1
        stack.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)

    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while stack:
        x, y = stack.pop()

        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)

        if x > 0:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y > 0:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    return rgba


def _process_sheet(source_bytes: bytes, request: AssetForgeRequest) -> tuple[list[tuple[str, bytes]], bytes]:
    if request.generation_layout == "single_character":
        return _process_single_image(source_bytes, request)
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
        branded, _ = stamp_image_bytes(output.getvalue(), preserve_alpha=True)
        files.append((filename, branded))

    return files, source_bytes


def _process_single_image(source_bytes: bytes, request: AssetForgeRequest) -> tuple[list[tuple[str, bytes]], bytes]:
    """Preserve the complete provider composition; no grid, matte, branding or resizing."""
    return process_single_image(source_bytes, request)


def _output_manifest(request: AssetForgeRequest, files: list[tuple[str, bytes]], source_bytes: bytes,
                     reference_bytes: bytes | None, generation_mode: str) -> dict:
    return {
        "schema_version": 1,
        "generation_layout": request.generation_layout,
        "generation_mode": generation_mode,
        "character": request.character,
        "quantity": request.quantity,
        "pose_intent": request.pose_intent,
        "expression": request.expression,
        "framing": request.framing,
        "wardrobe_variant": request.wardrobe_variant,
        "effective_wardrobe": "default" if (request.campaign_id or "").strip().lower() == "manifest_glow_lab" and request.character.strip().lower() == "ceo" else request.wardrobe_variant,
        "campaign_id": request.campaign_id,
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest() if reference_bytes else None,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "raw_source_path": "raw/provider_image.bin" if request.generation_layout == "single_character" else None,
        "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "media_type": "image/png"} for name, data in files],
    }


def _pack_name(request: AssetForgeRequest) -> str:
    suffix = "single" if request.generation_layout == "single_character" else f"{request.quantity}pack"
    return f"{request.character}_{request.product}_{suffix}".replace(" ", "_")


def _zip_files(
    files: list[tuple[str, bytes]],
    request: AssetForgeRequest,
    source_bytes: bytes,
    manifest: dict | None = None,
) -> bytes:
    """Package processed stickers together with the original generated master sheet."""
    return _zip_image_files(files, _pack_name(request), source_bytes, manifest,
                            single_image=request.generation_layout == "single_character")


def _zip_image_files(files, pack_name, source_bytes, manifest=None, *, single_image=True, include_raw_provider=True):
    """Retained ZIP writer for reviewed images; performs no generation or I/O."""
    output = io.BytesIO()

    with Image.open(io.BytesIO(source_bytes)) as source_image:
        master_output = io.BytesIO()
        source_image.convert("RGBA").save(master_output, format="PNG", optimize=True)
        master_png = master_output.getvalue()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        source_name = "original_image.png" if single_image else "original_sheet.png"
        archive.writestr(f"{pack_name}/master/{source_name}", master_png)
        if single_image and include_raw_provider:
            archive.writestr(f"{pack_name}/raw/provider_image.bin", source_bytes)
        if manifest is not None:
            archive.writestr(f"{pack_name}/manifest.json", json.dumps(manifest, ensure_ascii=False))
        for filename, data in files:
            archive.writestr(f"{pack_name}/{filename}", data)
    return output.getvalue()


def _embedded_workers_enabled() -> bool:
    return explicitly_enabled("SOLOFORGE_RUN_EMBEDDED_WORKERS")


@app.on_event("startup")
async def start_content_workers() -> None:
    if not _embedded_workers_enabled():
        print("embedded_content_workers_disabled")
        return
    asyncio.create_task(content_worker_loop())
    asyncio.create_task(content_router_loop())
    asyncio.create_task(content_asset_worker_loop())
    asyncio.create_task(audio_worker_loop())
    asyncio.create_task(final_render_worker_loop())


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "asset-forge",
        "git_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
    }


@app.get("/v1/content-video/{job_id}")
def download_final_content_video(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> RedirectResponse:
    require_soloforge_session(authorization)
    try:
        signed_url = create_signed_video_url(job_id, expires_in=600)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not prepare final video download") from exc
    return RedirectResponse(url=signed_url, status_code=307)


@app.post("/v1/asset-forge/generate", response_model=AssetForgeResponse)
def generate_asset_pack(
    request: AssetForgeRequest,
    authorization: str | None = Header(default=None),
) -> AssetForgeResponse:
    access_token = get_pollinations_access_token_from_authorization(authorization)
    return build_asset_pack(request, access_token=access_token)


def build_asset_pack(
    request: AssetForgeRequest, *, access_token: str | None, _byop_context: dict | None = None,
) -> AssetForgeResponse:
    """Shared processing contract; a credential never replaces execution approval."""
    single = request.generation_layout == "single_character"
    if single and not access_token:
        raise HTTPException(status_code=401, detail="Connect Pollinations before single-character generation")
    if access_token:
        require_generation_execution()

    try:
        reference_bytes = (_load_character_reference(request.character) if _byop_context is None
                           else _byop_context["reference_bytes"])
        if _character_key(request.character) in {"pearli", "ceo"} and reference_bytes is None:
            raise HTTPException(
                status_code=409,
                detail="Approved character master reference is missing from the SoloForge character library.",
            )

        if single and hashlib.sha256(reference_bytes).hexdigest() != CEO_MASTER_SHA256:
            raise HTTPException(status_code=409, detail="CEO master reference hash does not match the approved master")
        columns, rows = (1, 1) if single else _grid(request.quantity)
        prompt = _build_prompt(request, columns, rows, reference_bytes is not None) if _byop_context is None else _byop_context["prompt"]
        if _byop_context is not None:
            from backend.byop_ledger import digest
            if (not single or digest(request.model_dump()) != _byop_context["request_sha256"]
                    or hashlib.sha256(prompt.encode()).hexdigest() != _byop_context["prompt_sha256"]):
                raise HTTPException(409, "BYOP immutable generation context does not match the request")

        generation_mode = "local_fallback"
        if access_token:
            try:
                source_bytes = (_generate_sheet(prompt, reference_bytes, access_token) if _byop_context is None
                                else _generate_sheet(prompt, reference_bytes, access_token,
                                                     settings=_byop_context["provider_settings"]))
                if not single:
                    source_bytes, _ = stamp_image_bytes(source_bytes)
                generation_mode = "pollinations"
            except HTTPException as exc:
                if single:
                    raise HTTPException(status_code=exc.status_code, detail="Single-image provider result failed or is ambiguous. Do not automatically retry.") from exc
                print(
                    "asset_forge_pollinations_fallback",
                    {
                        "status_code": exc.status_code,
                        "detail": str(exc.detail)[:240],
                    },
                )
                source_bytes = _generate_local_fallback_sheet(request, reference_bytes)
        else:
            source_bytes = _generate_local_fallback_sheet(request, reference_bytes)

        files, source_bytes = _process_sheet(source_bytes, request)
        manifest = _output_manifest(request, files, source_bytes, reference_bytes, generation_mode)
        zip_bytes = _zip_files(files, request, source_bytes, manifest)

        pack_name = _pack_name(request)
        return AssetForgeResponse(
            asset_pack_name=pack_name,
            files=[name for name, _ in files],
            zip_base64=base64.b64encode(zip_bytes).decode("ascii"),
            source_image_base64=base64.b64encode(source_bytes).decode("ascii"),
            generation_mode=generation_mode,
            generation_layout=request.generation_layout,
            output_manifest=manifest,
        )
    except HTTPException:
        raise
    except Exception as exc:
        error_text = str(exc).strip() or exc.__class__.__name__
        raise HTTPException(
            status_code=500,
            detail=f"Asset Forge processing failed: {error_text[:1200]}",
        ) from exc
