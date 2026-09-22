"""Driving the checks over a parsed deck."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from presentation_maker.deck.checks.base import Check, CheckContext, Diagnostic, Severity
from presentation_maker.deck.checks.registry import REGISTRY
from presentation_maker.deck.models import DeckModel

__all__ = ["INTERNAL_ERROR_RULE", "run_checks"]

INTERNAL_ERROR_RULE = "internal-error"


def run_checks(
    deck: DeckModel,
    *,
    build_dir: Path | None = None,
    checks: Sequence[Check] = REGISTRY,
    only: Iterable[str] = (),
    ignore: Iterable[str] = (),
) -> tuple[Diagnostic, ...]:
    """Run `checks` against `deck` and return their diagnostics in source order.

    A check that raises becomes an `internal-error` diagnostic rather than an
    exception: a report that loses four rules because the fifth had a bad day is
    worse than a report that says so.
    """
    selected = _select(checks, only=frozenset(only), ignore=frozenset(ignore))
    context = CheckContext(deck=deck, build_dir=build_dir)

    found: list[Diagnostic] = []
    for check in selected:
        try:
            found.extend(check(context))
        except Exception as error:  # one bad rule must not cost the whole report
            found.append(_internal_error(check, error, deck))

    return tuple(sorted(found, key=_position))


def _select(
    checks: Sequence[Check], *, only: frozenset[str], ignore: frozenset[str]
) -> tuple[Check, ...]:
    return tuple(
        check
        for check in checks
        if (not only or check.rule in only) and check.rule not in ignore
    )


def _internal_error(check: Check, error: Exception, deck: DeckModel) -> Diagnostic:
    return Diagnostic(
        rule=INTERNAL_ERROR_RULE,
        severity=Severity.WARNING,
        message=f"The {check.rule!r} check failed: {type(error).__name__}: {error}",
        hint="This is a bug in pres check, not in the deck.",
        file=deck.source,
        line=1,
    )


def _position(diagnostic: Diagnostic) -> tuple[str, int, int, str]:
    return (str(diagnostic.file), diagnostic.line, diagnostic.column, diagnostic.rule)
