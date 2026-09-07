"""Filenames for captured images.

Names are sortable and self-describing so a directory listing reads like a
storyboard: `slide-03-the-failure-categories-f2.png` is the second fragment step
of slide 3.
"""

from __future__ import annotations

import re

from presentation_maker.capture_models import SlideRef

_UNSAFE = re.compile(r"[^a-z0-9-]+")
_MAX_ID_LENGTH = 60


def slide_stem(slide: SlideRef) -> str:
    """Base name for a slide, e.g. `slide-03-the-failure-categories`."""
    base = f"slide-{slide.index:02d}"
    safe_id = sanitize_id(slide.slide_id)
    return f"{base}-{safe_id}" if safe_id else base


def slide_filename(slide: SlideRef) -> str:
    return f"{slide_stem(slide)}.png"


def fragment_filename(slide: SlideRef, step: int) -> str:
    """`step` 0 is the slide before any fragment is revealed."""
    return f"{slide_stem(slide)}-f{step}.png"


def frame_filename(slide: SlideRef, elapsed_ms: int) -> str:
    """Timed animation frame, named by milliseconds since the slide settled."""
    return f"{slide_stem(slide)}-t{elapsed_ms:04d}.png"


def sanitize_id(slide_id: str) -> str:
    cleaned = _UNSAFE.sub("-", slide_id.strip().lower()).strip("-")
    return cleaned[:_MAX_ID_LENGTH].rstrip("-")
