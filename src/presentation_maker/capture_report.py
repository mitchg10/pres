"""Post-processing for a capture: the contact sheet and the text report.

The report matters as much as the images — "font awesome failed to load" is
directly actionable, whereas the same problem in a PNG just looks like missing
icons that an agent may not notice at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from presentation_maker.capture_models import CaptureResult

CONTACT_SHEET_NAME = "contact-sheet.png"
REPORT_NAME = "capture-report.md"

_COLUMNS = 3
_TILE_WIDTH = 620
_CAPTION_HEIGHT = 22
_PADDING = 10
_BACKGROUND = (24, 24, 27)
_CAPTION_COLOR = (235, 235, 235)


def build_contact_sheet(images: Sequence[Path], out_path: Path) -> Path | None:
    """Tile `images` into one labelled grid so a whole deck reads in a single look."""
    if not images:
        return None

    from PIL import Image, ImageDraw

    tiles = [_load_tile(Image, path) for path in images]
    tile_height = max(tile.height for tile in tiles)
    columns = min(_COLUMNS, len(tiles))
    rows = -(-len(tiles) // columns)  # ceiling division

    cell_width = _TILE_WIDTH + _PADDING
    cell_height = tile_height + _CAPTION_HEIGHT + _PADDING
    sheet = Image.new(
        "RGB",
        (columns * cell_width + _PADDING, rows * cell_height + _PADDING),
        _BACKGROUND,
    )
    draw = ImageDraw.Draw(sheet)

    for position, (tile, path) in enumerate(zip(tiles, images, strict=True)):
        left = _PADDING + (position % columns) * cell_width
        top = _PADDING + (position // columns) * cell_height
        sheet.paste(tile, (left, top))
        draw.text((left, top + tile_height + 4), path.stem, fill=_CAPTION_COLOR)

    sheet.save(out_path)
    return out_path


def _load_tile(image_module, path: Path):
    tile = image_module.open(path).convert("RGB")
    return _scaled(image_module, tile, _TILE_WIDTH)


def resize_to_width(path: Path, width: int) -> Path:
    """Shrink an image in place to `width`, preserving its aspect ratio.

    A poster is captured at its true 24×36in pixel size because its layout is
    physically fixed; that is a ~2MB PNG, so the file is scaled down afterwards
    to the width the caller actually asked for.
    """
    from PIL import Image

    with Image.open(path) as image:
        if image.width <= width:
            return path
        _scaled(Image, image.convert("RGB"), width).save(path)
    return path


def _scaled(image_module, image, width: int):
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), image_module.LANCZOS)


def write_report(result: CaptureResult, out_path: Path) -> Path:
    """Write `capture-report.md` describing what was captured and what looked wrong."""
    out_path.write_text(_render_report(result), encoding="utf-8")
    return out_path


def _render_report(result: CaptureResult) -> str:
    sections = [
        f"# Capture report — {result.slug}",
        "",
        f"Output directory: `{result.out_dir}`",
        "",
        _list_section("Images", [f"`{path.name}`" for path in result.images]),
        _list_section("Content overflow", result.overflow, empty="No content escaped a slide."),
        _list_section(
            "Console errors",
            result.console_errors,
            empty="No console errors or warnings.",
        ),
        _list_section(
            "Failed requests",
            result.failed_requests,
            empty="No failed requests.",
            note=(
                "The decks load GSAP and Font Awesome from CDNs; failures here mean "
                "icons or animations are missing from the screenshots, not from the deck."
            ),
        ),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _list_section(
    title: str,
    items: Sequence[str],
    *,
    empty: str = "Nothing captured.",
    note: str | None = None,
) -> str:
    lines = [f"## {title}", ""]
    if items:
        lines = [*lines, *(f"- {item}" for item in items)]
        if note:
            lines = [*lines, "", note]
    else:
        lines = [*lines, empty]
    return "\n".join([*lines, ""])
