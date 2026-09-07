"""End-to-end capture against a real deck.

Marked slow because it launches Chromium and may run `quarto render`; skipped
when the repo has no presentations to shoot. Run with `uv run pytest -m slow`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker import generator, screenshot
from presentation_maker.capture_models import CaptureOptions

pytestmark = pytest.mark.slow


@pytest.fixture
def deck() -> tuple[str, Path]:
    presentations = generator.list_presentations()
    if not presentations:
        pytest.skip("no presentations in this checkout")
    first = presentations[0]
    return first["slug"], Path(first["path"])


def test_capturing_one_slide_writes_a_real_png(deck: tuple[str, Path], tmp_path: Path) -> None:
    slug, pres_dir = deck
    options = CaptureOptions(slides="0", out_dir=tmp_path, width=640, height=360)

    result = screenshot.capture_presentation(slug, pres_dir, generator.PROJECT_ROOT, options)

    assert len(result.images) == 1
    image = result.images[0]
    assert image.exists() and image.stat().st_size > 0
    assert result.report is not None and result.report.exists()


def test_an_unknown_slide_id_is_rejected(deck: tuple[str, Path], tmp_path: Path) -> None:
    slug, pres_dir = deck
    options = CaptureOptions(slides="no-such-slide", out_dir=tmp_path)

    with pytest.raises(ValueError, match="No slide with id"):
        screenshot.capture_presentation(slug, pres_dir, generator.PROJECT_ROOT, options)
