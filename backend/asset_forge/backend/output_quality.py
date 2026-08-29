from __future__ import annotations

import io
from collections import deque
from typing import Protocol

from PIL import Image, ImageFilter

from .grid_policy import exact_grid


OUTPUT_SIZE = 512
OUTPUT_PADDING = 40
BACKGROUND_THRESHOLD = 8
EDGE_BLUR_RADIUS = 1.15
MIN_CELL_CLEARANCE_RATIO = 0.025
MIN_FOREGROUND_RATIO = 0.015
MAX_FOREGROUND_RATIO = 0.72
MAX_CONTENT_SPAN_RATIO = 0.95
COMPONENT_ALPHA_THRESHOLD = 64
MIN_SUBSTANTIAL_COMPONENT_RATIO = 0.02
SECOND_COMPONENT_RELATIVE_RATIO = 0.35
CORE_ALPHA_THRESHOLD = 128
CORE_EROSION_SIZE = 7
CORE_MIN_COMPONENT_RATIO = 0.012
CORE_SECOND_RELATIVE_RATIO = 0.28


class StickerSheetQualityError(ValueError):
    """Raised when a generated sheet cannot safely be split into usable stickers."""


class AssetForgeRequestLike(Protocol):
    quantity: int
    character: str


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
    """Return an L mask where border-connected background is 0 and foreground is 255."""
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


def _defringe_rgb(rgba: Image.Image, alpha: Image.Image) -> Image.Image:
    """Propagate foreground RGB through every nonzero soft-edge alpha pixel."""
    output = rgba.copy()
    source_pixels = rgba.load()
    output_pixels = output.load()
    alpha_pixels = alpha.load()
    width, height = rgba.size

    if width == 0 or height == 0:
        output.putalpha(alpha)
        return output

    max_alpha = alpha.getextrema()[1]
    if max_alpha <= 0:
        output.putalpha(alpha)
        return output

    seed_threshold = min(250, max_alpha)
    propagated: list[tuple[int, int, int] | None] = [None] * (width * height)
    queue: deque[tuple[int, int]] = deque()

    for y in range(height):
        row = y * width
        for x in range(width):
            if alpha_pixels[x, y] >= seed_threshold:
                propagated[row + x] = source_pixels[x, y][:3]
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        color = propagated[y * width + x]
        if color is None:
            continue

        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            index = ny * width + nx
            if alpha_pixels[nx, ny] <= 0 or propagated[index] is not None:
                continue
            propagated[index] = color
            queue.append((nx, ny))

    for y in range(height):
        row = y * width
        for x in range(width):
            a = alpha_pixels[x, y]
            if a <= 0 or a >= 255:
                continue
            color = propagated[row + x]
            if color is not None:
                output_pixels[x, y] = (*color, source_pixels[x, y][3])

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
    original_alpha = rgba.getchannel("A")
    alpha = Image.new("L", rgba.size, 0)
    alpha_pixels = alpha.load()
    softened_pixels = foreground_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius)).load()
    original_pixels = original_alpha.load()

    for y in range(rgba.height):
        for x in range(rgba.width):
            alpha_pixels[x, y] = min(original_pixels[x, y], softened_pixels[x, y])

    return _defringe_rgb(rgba, alpha)


def _component_sizes(alpha: Image.Image, *, threshold: int = COMPONENT_ALPHA_THRESHOLD) -> list[int]:
    """Return connected foreground component sizes, largest first."""
    width, height = alpha.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    components: list[int] = []

    for y in range(height):
        for x in range(width):
            index = y * width + x
            if visited[index] or pixels[x, y] < threshold:
                continue

            visited[index] = 1
            queue: deque[tuple[int, int]] = deque([(x, y)])
            size = 0
            while queue:
                px, py = queue.popleft()
                size += 1
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if nx < 0 or nx >= width or ny < 0 or ny >= height:
                        continue
                    neighbour = ny * width + nx
                    if visited[neighbour] or pixels[nx, ny] < threshold:
                        continue
                    visited[neighbour] = 1
                    queue.append((nx, ny))
            components.append(size)

    components.sort(reverse=True)
    return components


def _has_multiple_substantial_components(
    components: list[int],
    *,
    cell_area: int,
    min_area_ratio: float,
    second_relative_ratio: float,
) -> bool:
    if len(components) < 2:
        return False
    largest, second = components[0], components[1]
    return (
        second / max(1, cell_area) >= min_area_ratio
        and second / max(1, largest) >= second_relative_ratio
    )


def _validate_single_substantial_subject(alpha: Image.Image, *, index: int) -> None:
    cell_area = max(1, alpha.width * alpha.height)

    components = _component_sizes(alpha)
    duplicate = _has_multiple_substantial_components(
        components,
        cell_area=cell_area,
        min_area_ratio=MIN_SUBSTANTIAL_COMPONENT_RATIO,
        second_relative_ratio=SECOND_COMPONENT_RELATIVE_RATIO,
    )

    if not duplicate and alpha.width >= CORE_EROSION_SIZE and alpha.height >= CORE_EROSION_SIZE:
        strong = alpha.point(lambda value: 255 if value >= CORE_ALPHA_THRESHOLD else 0)
        eroded = strong.filter(ImageFilter.MinFilter(size=CORE_EROSION_SIZE))
        core_components = _component_sizes(eroded, threshold=128)
        duplicate = _has_multiple_substantial_components(
            core_components,
            cell_area=cell_area,
            min_area_ratio=CORE_MIN_COMPONENT_RATIO,
            second_relative_ratio=CORE_SECOND_RELATIVE_RATIO,
        )

    if duplicate:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: cell {index + 1} contains multiple substantial subjects. "
            "Each cell must contain exactly one usable sticker character; please regenerate."
        )


def _validate_cell(processed: Image.Image, *, index: int) -> None:
    """Ensure one sticker is isolated inside a cell before it is exported."""
    alpha = processed.getchannel("A")
    bbox = alpha.getbbox()
    width, height = processed.size

    if not bbox:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: cell {index + 1} is empty. Please regenerate the sheet."
        )

    left, top, right, bottom = bbox
    clearance = max(4, round(min(width, height) * MIN_CELL_CLEARANCE_RATIO))
    margins = (left, top, width - right, height - bottom)
    if min(margins) < clearance:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: artwork crosses the boundary of cell {index + 1}. "
            "The generated sheet cannot be split safely; please regenerate."
        )

    content_width = right - left
    content_height = bottom - top
    if content_width / width > MAX_CONTENT_SPAN_RATIO or content_height / height > MAX_CONTENT_SPAN_RATIO:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: cell {index + 1} contains oversized or clipped artwork. "
            "Please regenerate the sheet."
        )

    strong_foreground = sum(1 for value in alpha.getdata() if value >= 32)
    foreground_ratio = strong_foreground / max(1, width * height)
    if foreground_ratio < MIN_FOREGROUND_RATIO:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: cell {index + 1} does not contain a usable sticker. "
            "Please regenerate the sheet."
        )
    if foreground_ratio > MAX_FOREGROUND_RATIO:
        raise StickerSheetQualityError(
            f"Sticker sheet quality check failed: cell {index + 1} is dominated by oversized artwork. "
            "Please regenerate the sheet."
        )

    _validate_single_substantial_subject(alpha, index=index)


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
    """Validate, split, matte, defringe, and standardize a generated sticker sheet."""
    columns, rows = exact_grid(request.quantity)
    source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    cell_width = source.width // columns
    cell_height = source.height // rows

    if cell_width <= 0 or cell_height <= 0:
        raise StickerSheetQualityError("Sticker sheet quality check failed: generated sheet dimensions are invalid.")

    processed_cells: list[Image.Image] = []
    for index in range(request.quantity):
        row = index // columns
        column = index % columns
        left = column * cell_width
        top = row * cell_height
        right = source.width if column == columns - 1 else (column + 1) * cell_width
        bottom = source.height if row == rows - 1 else (row + 1) * cell_height

        crop = source.crop((left, top, right, bottom))
        processed = remove_background_soft(crop)
        _validate_cell(processed, index=index)
        processed_cells.append(processed)

    files: list[tuple[str, bytes]] = []
    for index, processed in enumerate(processed_cells):
        canvas = standardize_sticker(processed)
        filename = f"{index + 1:02d}_{request.character.lower()}_sticker.png"
        output = io.BytesIO()
        canvas.save(output, format="PNG", optimize=True)
        files.append((filename, output.getvalue()))

    return files, source_bytes
