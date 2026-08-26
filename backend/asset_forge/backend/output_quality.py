from __future__ import annotations

import io
from collections import deque
from typing import Protocol

from PIL import Image, ImageFilter


OUTPUT_SIZE = 512
OUTPUT_PADDING = 40
BACKGROUND_THRESHOLD = 8
EDGE_BLUR_RADIUS = 1.15
DEFRINGE_RADIUS = 2


class AssetForgeRequestLike(Protocol):
    quantity: int
    character: str


def _grid(quantity: int) -> tuple[int, int]:
    import math

    columns = min(6, max(2, math.ceil(math.sqrt(quantity))))
    rows = math.ceil(quantity / columns)
    return columns, rows


def _sample_background_color(rgba: Image.Image) -> tuple[int, int, int]:
    width, height = rgba.size
    points = (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    )
    samples = [rgba.getpixel(point)[:3] for point in points]
    return tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))


def _connected_background_mask(
    rgba: Image.Image,
    *,
    threshold: int = BACKGROUND_THRESHOLD,
) -> Image.Image:
    """Return an L mask where border-connected background is 0 and foreground is 255.

    The flood fill remains deliberately strict so near-white foreground details,
    especially the CEO's white suit, are not erased together with a white sheet.
    """
    width, height = rgba.size
    if width == 0 or height == 0:
        return Image.new("L", rgba.size, 255)

    pixels = rgba.load()
    bg_r, bg_g, bg_b = _sample_background_color(rgba)
    background = bytearray(width * height)
    queued = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def is_background(x: int, y: int) -> bool:
        r, g, b, _ = pixels[x, y]
        distance = max(abs(r - bg_r), abs(g - bg_g), abs(b - bg_b))
        return distance <= threshold

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if queued[index] or not is_background(x, y):
            return
        queued[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        background[y * width + x] = 1
        if x > 0:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y > 0:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    mask = Image.new("L", (width, height), 255)
    mask_pixels = mask.load()
    for y in range(height):
        row = y * width
        for x in range(width):
            if background[row + x]:
                mask_pixels[x, y] = 0
    return mask


def _defringe_rgb(rgba: Image.Image, alpha: Image.Image, radius: int = DEFRINGE_RADIUS) -> Image.Image:
    """Replace RGB on semi-transparent edge pixels with nearby opaque foreground RGB.

    Feathering a white-background source without this step leaves a visible white
    halo on dark destinations. Copying the nearest opaque foreground color keeps
    the alpha transition soft without carrying the original white matte outward.
    """
    output = rgba.copy()
    source_pixels = rgba.load()
    output_pixels = output.load()
    alpha_pixels = alpha.load()
    width, height = rgba.size

    for y in range(height):
        for x in range(width):
            a = alpha_pixels[x, y]
            if a <= 0 or a >= 255:
                continue

            best: tuple[int, int, int] | None = None
            best_distance = 10_000
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if ny < 0 or ny >= height:
                    continue
                for dx in range(-radius, radius + 1):
                    nx = x + dx
                    if nx < 0 or nx >= width or alpha_pixels[nx, ny] < 250:
                        continue
                    distance = dx * dx + dy * dy
                    if distance < best_distance:
                        best_distance = distance
                        best = source_pixels[nx, ny][:3]

            if best is not None:
                output_pixels[x, y] = (*best, source_pixels[x, y][3])

    output.putalpha(alpha)
    return output


def remove_background_soft(
    image: Image.Image,
    *,
    threshold: int = BACKGROUND_THRESHOLD,
    blur_radius: float = EDGE_BLUR_RADIUS,
) -> Image.Image:
    """Remove border-connected light background with a soft, defringed alpha edge."""
    rgba = image.convert("RGBA")
    if rgba.width == 0 or rgba.height == 0:
        return rgba

    foreground_mask = _connected_background_mask(rgba, threshold=threshold)
    alpha = foreground_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    original_alpha = rgba.getchannel("A")
    alpha = Image.new("L", rgba.size, 0)
    alpha_pixels = alpha.load()
    softened_pixels = foreground_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius)).load()
    original_pixels = original_alpha.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            alpha_pixels[x, y] = min(original_pixels[x, y], softened_pixels[x, y])

    return _defringe_rgb(rgba, alpha)


def standardize_sticker(
    image: Image.Image,
    *,
    size: int = OUTPUT_SIZE,
    padding: int = OUTPUT_PADDING,
) -> Image.Image:
    """Fit a transparent sticker onto a fixed square canvas without stretching."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if not bbox:
        return canvas

    content = rgba.crop(bbox)
    max_content = max(1, size - padding * 2)
    scale = min(max_content / content.width, max_content / content.height)
    target_width = max(1, round(content.width * scale))
    target_height = max(1, round(content.height * scale))
    content = content.resize((target_width, target_height), Image.Resampling.LANCZOS)

    x = (size - target_width) // 2
    y = (size - target_height) // 2
    canvas.alpha_composite(content, (x, y))
    return canvas


def process_sheet(
    source_bytes: bytes,
    request: AssetForgeRequestLike,
) -> tuple[list[tuple[str, bytes]], bytes]:
    """Split, matte, defringe, and standardize a generated sticker sheet."""
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
        processed = remove_background_soft(crop)
        canvas = standardize_sticker(processed)

        filename = f"{index + 1:02d}_{request.character.lower()}_sticker.png"
        output = io.BytesIO()
        canvas.save(output, format="PNG", optimize=True)
        files.append((filename, output.getvalue()))

    return files, source_bytes
