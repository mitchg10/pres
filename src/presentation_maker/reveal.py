"""Driving a rendered reveal.js deck from Playwright.

All the deck-specific JavaScript lives here so the capture engine stays readable.
The decks are generated with `hash: true`, `hashOneBasedIndex: false` and
`jumpToSlide: true` (see templates.render_quarto_yml), so slide N is `#/N`
zero-based and `Reveal.slide(...)` navigation is available.
"""

from __future__ import annotations

from typing import Any

from presentation_maker.capture_models import SlideRef

_NAV_TIMEOUT_MS = 10_000

_LIST_SLIDES = """
() => Array.from(document.querySelectorAll('.reveal .slides > section')).map(
    (section, index) => ({ index, slideId: section.id || '' })
)
"""

# Fragments sharing a data-fragment-index are revealed together, so the number of
# distinct indices is the number of steps — not the number of .fragment elements.
_COUNT_FRAGMENT_STEPS = """
() => {
    const slide = window.Reveal && window.Reveal.getCurrentSlide();
    if (!slide) return 0;
    const fragments = Array.from(slide.querySelectorAll('.fragment'));
    return new Set(fragments.map((el) => el.getAttribute('data-fragment-index'))).size;
}
"""

NO_FRAGMENTS = -1
"""reveal's fragment index for "nothing revealed yet"."""

# Content that spills past the slide box is the most common regression after a
# styles/components.scss edit, and it is far easier to spot in numbers than in a
# screenshot an agent has to eyeball.
_MEASURE_OVERFLOW = """
() => {
    const reveal = window.Reveal;
    const slide = reveal && reveal.getCurrentSlide();
    if (!slide) return null;
    const bounds = slide.getBoundingClientRect();
    const tolerance = 2;
    const describe = (el) => {
        const classes = (el.getAttribute('class') || '').trim().split(/\\s+/).filter(Boolean);
        return el.tagName.toLowerCase() + (classes.length ? '.' + classes.join('.') : '');
    };
    const escaping = Array.from(slide.querySelectorAll('*')).filter((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.height <= 0 || rect.width <= 0) return false;
        return rect.bottom > bounds.bottom + tolerance || rect.right > bounds.right + tolerance;
    });
    return {
        scrollHeight: Math.round(slide.scrollHeight),
        clientHeight: Math.round(slide.clientHeight),
        escaping: escaping.slice(0, 5).map(describe),
    };
}
"""


def list_slides(page: Any) -> tuple[SlideRef, ...]:
    """Every top-level slide in the deck, in presentation order."""
    entries = page.evaluate(_LIST_SLIDES)
    return tuple(
        SlideRef(index=entry["index"], slide_id=entry["slideId"]) for entry in entries
    )


def goto_slide(
    page: Any,
    index: int,
    *,
    fragment: int = NO_FRAGMENTS,
    settle_ms: int = 0,
) -> None:
    """Navigate to a slide (and a fragment state), waiting for reveal to land.

    Navigation goes through `Reveal.slide` rather than class manipulation so the
    deck's own `slidechanged` handlers run — `logo-inject.html` swaps the slide
    logo in one, and a hand-rolled state change would leave it stale.
    """
    page.evaluate(
        "([index, fragment]) => window.Reveal.slide(index, 0, fragment)",
        [index, fragment],
    )
    page.wait_for_function(
        "(index) => window.Reveal.getIndices().h === index",
        arg=index,
        timeout=_NAV_TIMEOUT_MS,
    )
    if settle_ms:
        page.wait_for_timeout(settle_ms)


def count_fragment_steps(page: Any) -> int:
    """How many distinct reveal steps the current slide has."""
    return int(page.evaluate(_COUNT_FRAGMENT_STEPS))


def measure_overflow(page: Any) -> str | None:
    """Describe content escaping the current slide, or None if it all fits."""
    measurement = page.evaluate(_MEASURE_OVERFLOW)
    if not measurement:
        return None

    problems: list[str] = []
    scroll_height = measurement["scrollHeight"]
    client_height = measurement["clientHeight"]
    if client_height and scroll_height > client_height + 2:
        problems = [*problems, f"content is {scroll_height - client_height}px taller than the slide"]
    escaping = measurement["escaping"]
    if escaping:
        problems = [*problems, "elements past the slide edge: " + ", ".join(escaping)]
    return "; ".join(problems) if problems else None
