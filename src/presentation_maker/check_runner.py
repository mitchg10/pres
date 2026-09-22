"""Gathering decks and running the checks over them.

Sits between the CLI and `deck.checks` so the command stays a thin shell: this module
knows about slugs and directories, the library below it knows only about paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from presentation_maker.check_models import CheckReport, DeckReport
from presentation_maker.deck.checks import Diagnostic, Severity, run_checks
from presentation_maker.deck.parser import parse_deck

__all__ = ["DeckNotFoundError", "check_decks", "exit_code", "find_decks"]

SOURCE_NAME = "index.qmd"


class DeckNotFoundError(FileNotFoundError):
    """Named deck does not exist, or the tree holds no decks at all."""


def find_decks(presentations_dir: Path, names: Sequence[str] = ()) -> tuple[Path, ...]:
    """Resolve deck names to their source files, or find every deck when none given."""
    if not presentations_dir.is_dir():
        raise DeckNotFoundError(f"No presentations directory at {presentations_dir}.")

    if not names:
        found = tuple(sorted(presentations_dir.glob(f"*/{SOURCE_NAME}")))
        if not found:
            raise DeckNotFoundError(f"No presentations found in {presentations_dir}.")
        return found

    sources: list[Path] = []
    for name in names:
        source = presentations_dir / name / SOURCE_NAME
        if not source.is_file():
            raise DeckNotFoundError(f"No presentation named '{name}'.")
        sources.append(source)
    return tuple(sources)


def check_decks(
    sources: Sequence[Path],
    *,
    use_build: bool = True,
    only: Iterable[str] = (),
    ignore: Iterable[str] = (),
    minimum: Severity = Severity.WARNING,
) -> CheckReport:
    """Parse and check each deck, keeping diagnostics at or above `minimum`."""
    reports = []
    for source in sources:
        deck = parse_deck(source)
        found = run_checks(
            deck,
            build_dir=source.parent if use_build else None,
            only=only,
            ignore=ignore,
        )
        kept = tuple(d for d in found if d.at_least(minimum))
        reports.append(DeckReport.from_deck(deck, kept))
    return CheckReport(decks=tuple(reports))


def exit_code(report: CheckReport, *, strict: bool = False) -> int:
    """0 clean, 1 problems found.

    Deliberately ruff/eslint-shaped rather than matching the rest of this CLI, where
    1 means "could not run". `cli.check` reserves 2 for that. Do not "fix" the
    divergence: a checker whose failure and whose findings share an exit code cannot
    be used in a pipeline.
    """
    failing: tuple[Diagnostic, ...] = tuple(
        d
        for d in report.diagnostics
        if d.severity is Severity.ERROR or (strict and d.severity is Severity.WARNING)
    )
    return 1 if failing else 0
