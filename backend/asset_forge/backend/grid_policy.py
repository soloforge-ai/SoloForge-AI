from __future__ import annotations

SUPPORTED_GRID_LAYOUTS: dict[int, tuple[int, int]] = {
    4: (2, 2),
    8: (4, 2),
    12: (4, 3),
    16: (4, 4),
    20: (5, 4),
    24: (6, 4),
}

MAX_SUPPORTED_QUANTITY = max(SUPPORTED_GRID_LAYOUTS)


def exact_grid(quantity: int) -> tuple[int, int]:
    """Return an exact grid with no unused cells for supported sticker pack sizes."""
    try:
        return SUPPORTED_GRID_LAYOUTS[quantity]
    except KeyError as exc:
        supported = ", ".join(str(value) for value in SUPPORTED_GRID_LAYOUTS)
        raise ValueError(
            f"Unsupported sticker quantity {quantity}. Supported pack sizes: {supported}."
        ) from exc
