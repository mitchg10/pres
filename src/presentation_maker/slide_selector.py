"""Turn a `--slide` selector string into concrete slide indices.

Kept free of Playwright so the parsing rules can be tested without a browser.
"""

from __future__ import annotations

from collections.abc import Sequence

from presentation_maker.capture_models import SlideRef

ALL = "all"


def parse_slide_selector(selector: str, slides: Sequence[SlideRef]) -> tuple[int, ...]:
    """Resolve `selector` against the deck's slides, returning zero-based indices.

    Accepts `all`, an index (`3`), a slide id (`the-failure-categories`), an
    inclusive range (`2-5`), or a comma-separated mix of those. Order is
    preserved and duplicates are dropped, so `3,3,1` captures slides 3 then 1.

    Raises ValueError with a message naming the valid options, since the usual
    caller is an agent that can act on a good error but not on a stack trace.
    """
    if not slides:
        raise ValueError("The deck contains no slides — check that it rendered correctly.")

    text = selector.strip()
    if not text or text.lower() == ALL:
        return tuple(slide.index for slide in slides)

    resolved: list[int] = []
    for token in (part.strip() for part in text.split(",")):
        if not token:
            continue
        resolved = [*resolved, *_resolve_token(token, slides)]

    if not resolved:
        raise ValueError(f"Slide selector '{selector}' did not name any slide.")
    return _deduplicate(resolved)


def _resolve_token(token: str, slides: Sequence[SlideRef]) -> tuple[int, ...]:
    bounds = _parse_range(token)
    if bounds is not None:
        start, end = bounds
        return tuple(index for index in range(start, end + 1) if _in_range(index, slides))

    if token.isdigit():
        index = int(token)
        if not _in_range(index, slides):
            raise ValueError(
                f"Slide {index} is out of range — this deck has {len(slides)} slides "
                f"(valid indices 0-{len(slides) - 1})."
            )
        return (index,)

    return (_resolve_id(token, slides),)


def _parse_range(token: str) -> tuple[int, int] | None:
    """Parse `2-5`, but only when both sides are numeric.

    Slide ids contain hyphens (`the-stress-test`), so a hyphen alone must not be
    read as a range.
    """
    start, separator, end = token.partition("-")
    if not separator or not start.isdigit() or not end.isdigit():
        return None
    low, high = int(start), int(end)
    return (low, high) if low <= high else (high, low)


def _resolve_id(token: str, slides: Sequence[SlideRef]) -> int:
    wanted = token.lstrip("#/").lower()
    for slide in slides:
        if slide.slide_id.lower() == wanted:
            return slide.index
    known = ", ".join(slide.slide_id for slide in slides if slide.slide_id) or "(none)"
    raise ValueError(f"No slide with id '{token}'. Available ids: {known}")


def _in_range(index: int, slides: Sequence[SlideRef]) -> bool:
    return 0 <= index < len(slides)


def _deduplicate(indices: Sequence[int]) -> tuple[int, ...]:
    seen: set[int] = set()
    ordered: list[int] = []
    for index in indices:
        if index not in seen:
            seen.add(index)
            ordered = [*ordered, index]
    return tuple(ordered)
