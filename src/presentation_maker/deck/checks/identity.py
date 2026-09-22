"""Checks about slide identity — the ids `pres shot --slide` selects on."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator

from presentation_maker.deck.checks.base import CheckContext, Diagnostic, Severity, check

__all__ = ["slide_id_drift", "slide_id_duplicate"]

_SECTION_ID_RE = re.compile(r'<section[^>]*\bid="([^"]*)"')
_TITLE_SLIDE_ID = "title-slide"


@check("slide-id-duplicate", Severity.ERROR)
def slide_id_duplicate(context: CheckContext) -> Iterator[Diagnostic]:
    """Two headings that slug the same way.

    Pandoc resolves the collision silently by appending `-1`, so the deck builds and
    looks fine — but `--slide <id>` then captures the *first* of the two, which is
    rarely the one anybody meant.
    """
    counts = Counter(slide.base_id for slide in context.deck.slides)
    seen: Counter[str] = Counter()

    for slide in context.deck.slides:
        seen[slide.base_id] += 1
        if counts[slide.base_id] < 2 or seen[slide.base_id] == 1:
            continue
        yield Diagnostic(
            rule="slide-id-duplicate",
            severity=Severity.ERROR,
            message=(
                f"Heading {slide.heading!r} repeats the slide id {slide.base_id!r}; "
                f"pandoc renamed this one to {slide.slide_id!r}."
            ),
            hint=(
                f"Give it an explicit id — '## {slide.heading} "
                "{#a-distinct-id}' — or reword the heading."
            ),
            file=slide.origin.file,
            line=slide.origin.line,
            column=slide.origin.column,
            slide_id=slide.slide_id,
            slide_index=slide.index,
        )


@check("slide-id-drift", Severity.WARNING)
def slide_id_drift(context: CheckContext) -> Iterator[Diagnostic]:
    """The built deck's slide ids disagree with the source's.

    Almost always a stale `index.html`; occasionally a sign that the slug rule here
    has drifted from pandoc's. Either way, ids taken from the build will not select
    the slides the source describes.
    """
    html = context.built_html
    if html is None:
        return

    built = tuple(i for i in _SECTION_ID_RE.findall(html.read_text(encoding="utf-8")) if i != _TITLE_SLIDE_ID)
    parsed = context.deck.slide_ids()
    if built == parsed:
        return

    missing = [i for i in parsed if i not in built]
    extra = [i for i in built if i not in parsed]
    yield Diagnostic(
        rule="slide-id-drift",
        severity=Severity.WARNING,
        message=(
            f"The built deck has {len(built)} slides, the source has {len(parsed)}. "
            f"Only in source: {missing or '-'}. Only in build: {extra or '-'}."
        ),
        hint="Re-render the deck; `pres shot` does it for you.",
        file=context.deck.source,
        line=1,
    )
