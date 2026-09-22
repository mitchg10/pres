"""What `pres check` produces.

Kept separate from `deck.checks` so the library stays free of any notion of a "run":
a check yields diagnostics about one deck, and this is the shape a *command* returns.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from presentation_maker.deck.checks import Diagnostic, Severity
from presentation_maker.deck.models import DeckModel

__all__ = ["CheckReport", "DeckReport", "SlideSummary"]


class SlideSummary(BaseModel):
    """One slide, as `--json` consumers want to see it.

    This array is the reason `pres check <deck> --json` supersedes
    `deck-index.py --deck <slug>`: same information, derived from a tested parser.
    """

    model_config = ConfigDict(frozen=True)

    index: int
    slide_id: str
    heading: str
    file: Path
    line: int


class DeckReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    source: Path
    slides: tuple[SlideSummary, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    @classmethod
    def from_deck(cls, deck: DeckModel, diagnostics: tuple[Diagnostic, ...]) -> DeckReport:
        return cls(
            slug=deck.slug,
            source=deck.source,
            slides=tuple(
                SlideSummary(
                    index=slide.index,
                    slide_id=slide.slide_id,
                    heading=slide.heading,
                    file=slide.origin.file,
                    line=slide.origin.line,
                )
                for slide in deck.slides
            ),
            diagnostics=diagnostics,
        )


class CheckReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    decks: tuple[DeckReport, ...] = ()

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(d for deck in self.decks for d in deck.diagnostics)

    def count(self, severity: Severity) -> int:
        return sum(1 for d in self.diagnostics if d.severity is severity)

    @property
    def error_count(self) -> int:
        return self.count(Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return self.count(Severity.WARNING)
