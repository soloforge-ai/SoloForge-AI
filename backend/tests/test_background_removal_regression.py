from __future__ import annotations

from PIL import Image

from backend.asset_forge.main import _remove_simple_background


def _make_white_suit_regression_crop() -> Image.Image:
    """Build a deterministic white-background/white-suit regression fixture.

    The off-white foreground intentionally sits directly against a pure-white
    background. A background remover with a tolerance that is too generous
    will flood into the foreground and erase it, reproducing the A4 defect.
    """
    image = Image.new("RGBA", (64, 64), (255, 255, 255, 255))

    # Dark character core: shirt/tie area that must obviously remain foreground.
    for y in range(16, 54):
        for x in range(27, 37):
            image.putpixel((x, y), (28, 25, 26, 255))

    # White suit panels. These are deliberately close to the background color,
    # matching the failure mode seen on the real CEO sticker sheet.
    suit = (249, 247, 245, 255)
    for y in range(18, 54):
        for x in range(15, 27):
            image.putpixel((x, y), suit)
        for x in range(37, 49):
            image.putpixel((x, y), suit)

    # Off-white trousers.
    for y in range(46, 61):
        for x in range(22, 31):
            image.putpixel((x, y), suit)
        for x in range(33, 42):
            image.putpixel((x, y), suit)

    return image


def test_white_suit_survives_background_removal() -> None:
    source = _make_white_suit_regression_crop()
    processed = _remove_simple_background(source)

    protected_points = {
        "left_jacket": (20, 30),
        "right_jacket": (44, 30),
        "left_trouser": (26, 52),
        "right_trouser": (38, 52),
    }

    failures: list[str] = []
    for label, point in protected_points.items():
        alpha = processed.getpixel(point)[3]
        if alpha < 200:
            failures.append(f"{label}: alpha={alpha} at {point}")

    assert not failures, (
        "Background removal erased protected white-suit pixels: "
        + "; ".join(failures)
    )


def test_outer_white_background_becomes_transparent() -> None:
    source = _make_white_suit_regression_crop()
    processed = _remove_simple_background(source)

    for point in ((0, 0), (63, 0), (0, 63), (63, 63), (5, 5)):
        assert processed.getpixel(point)[3] == 0, (
            f"Background pixel remained opaque at {point}: "
            f"alpha={processed.getpixel(point)[3]}"
        )
