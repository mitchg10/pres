"""Adapting a source-parsed deck to the shapes the capture layer already speaks.

The payoff is that `slide_selector.parse_slide_selector` can validate a `--slide`
argument against source, before a render and a Chromium launch. A bad id then costs
milliseconds and produces the list of real ids, instead of costing a full build.
"""

from __future__ import annotations

from presentation_maker.capture_models import SlideRef
from presentation_maker.deck.models import DeckModel

__all__ = ["to_slide_refs"]


def to_slide_refs(model: DeckModel) -> tuple[SlideRef, ...]:
    """The deck's slides as reveal sees them, title slide included.

    Quarto's generated title slide has no `##` heading behind it, so it exists in the
    rendered deck but not in `model.slides`. It is prepended here, at index 0, with
    the id reveal gives it.
    """
    refs = [SlideRef(index=slide.index, slide_id=slide.slide_id) for slide in model.slides]
    if model.has_title_slide:
        refs.insert(0, SlideRef(index=0, slide_id="title-slide"))
    return tuple(refs)
