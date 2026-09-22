"""The shapes a parsed deck is made of.

Every model here is frozen. A parsed deck is a value: checks read it, none of them
write to it, and two parses of the same bytes compare equal. That also makes these
hashable, which the checks rely on when they dedupe diagnostics.

Positions are **1-based lines and columns**, because every consumer — editors, the
VS Code problem matcher, `file:line:col` output — counts that way. Slide *indices*
stay zero-based to match reveal's `#/N` hash and `pres shot --slide <n>`. The two
numbering schemes sit next to each other on purpose; do not unify them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

__all__ = [
    "AssetRef",
    "DeckModel",
    "IncludeRef",
    "PandocAttrs",
    "Slide",
    "SourceLine",
    "SourcePos",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class SourcePos(_Frozen):
    """Where something is, in the file a human would open to fix it."""

    file: Path
    line: int
    column: int = 1

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


class PandocAttrs(_Frozen):
    """A parsed ``{#id .class key="value"}`` block.

    `keyvals` is a tuple of pairs rather than a dict so the model stays hashable, and
    because pandoc permits a repeated key. Use `get()` for the common lookup.
    """

    identifier: str = ""
    classes: tuple[str, ...] = ()
    keyvals: tuple[tuple[str, str], ...] = ()

    def get(self, key: str, default: str | None = None) -> str | None:
        for candidate, value in self.keyvals:
            if candidate == key:
                return value
        return default

    def has_class(self, name: str) -> bool:
        return name in self.classes


class SourceLine(_Frozen):
    """One line of a deck after includes are spliced in.

    `origin` is the file the line was actually written in, which is the whole reason
    this type exists: a diagnostic about a line from `partials/_thank-you.qmd` has to
    point at that partial, not at the line number it landed on in `index.qmd`.
    """

    text: str
    origin: SourcePos
    depth: int = 0


class IncludeRef(_Frozen):
    """A ``{{< include ... >}}`` shortcode and what it resolved to."""

    raw: str
    resolved: Path | None
    origin: SourcePos


class AssetRef(_Frozen):
    """An image or other local file a slide points at."""

    raw: str
    resolved: Path | None
    origin: SourcePos
    slide_index: int | None = None
    slide_id: str = ""

    @property
    def is_external(self) -> bool:
        return self.resolved is None and _has_scheme(self.raw)


class Slide(_Frozen):
    """One ``##`` heading and everything under it."""

    index: int
    """Zero-based **reveal** index — the number `pres shot --slide <n>` takes.

    Quarto emits a title slide from the frontmatter, so this is one *more* than the
    heading's ordinal in the file. Getting that offset wrong sends every capture to
    the slide before the one the diagnostic meant.
    """

    slide_id: str
    base_id: str = ""
    """The id before pandoc's `-1`/`-2` disambiguation.

    Kept so `slide-id-duplicate` can see a collision that `slide_id` has already
    papered over: two headings that both slug to `learn-it` are a bug worth naming,
    even though the rendered deck resolves them to distinct ids.
    """

    heading: str
    attrs: PandocAttrs
    origin: SourcePos
    body: tuple[SourceLine, ...] = ()


class DeckModel(_Frozen):
    """A whole deck, parsed from source without rendering it."""

    slug: str
    deck_dir: Path
    source: Path
    frontmatter: dict[str, Any] = {}
    slides: tuple[Slide, ...] = ()
    includes: tuple[IncludeRef, ...] = ()
    assets: tuple[AssetRef, ...] = ()
    has_title_slide: bool = True
    """Whether Quarto generates a title slide, which occupies reveal index 0."""

    def slide_ids(self) -> tuple[str, ...]:
        return tuple(slide.slide_id for slide in self.slides)


def _has_scheme(raw: str) -> bool:
    lowered = raw.lower()
    return lowered.startswith(("http://", "https://", "data:", "//"))
