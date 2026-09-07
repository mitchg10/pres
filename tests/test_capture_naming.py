from __future__ import annotations

from presentation_maker.capture_models import SlideRef
from presentation_maker.capture_naming import (
    fragment_filename,
    frame_filename,
    sanitize_id,
    slide_filename,
)

SLIDE = SlideRef(index=3, slide_id="the-failure-categories")
UNTITLED = SlideRef(index=12, slide_id="")


def test_slide_filename_pads_the_index_so_names_sort() -> None:
    assert slide_filename(SLIDE) == "slide-03-the-failure-categories.png"


def test_slide_without_an_id_falls_back_to_the_index() -> None:
    assert slide_filename(UNTITLED) == "slide-12.png"


def test_fragment_filenames_are_numbered_from_zero() -> None:
    assert fragment_filename(SLIDE, 0) == "slide-03-the-failure-categories-f0.png"
    assert fragment_filename(SLIDE, 2) == "slide-03-the-failure-categories-f2.png"


def test_frame_filenames_are_padded_so_they_sort_by_time() -> None:
    assert frame_filename(SLIDE, 0) == "slide-03-the-failure-categories-t0000.png"
    assert frame_filename(SLIDE, 400) == "slide-03-the-failure-categories-t0400.png"
    assert frame_filename(SLIDE, 1200) == "slide-03-the-failure-categories-t1200.png"


def test_sanitize_id_strips_characters_that_are_awkward_in_a_filename() -> None:
    assert sanitize_id("Why AI? (Part 2)") == "why-ai-part-2"


def test_sanitize_id_never_leaves_a_trailing_separator() -> None:
    assert sanitize_id("trailing---") == "trailing"
    assert sanitize_id("x" * 80).endswith("x")
    assert len(sanitize_id("x" * 80)) == 60
