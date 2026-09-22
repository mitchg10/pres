"""Checks about paths written in the source that should name a file.

Images and includes are grouped together because they fail the same way: the deck
still builds, and the problem only shows up as a broken-image box or a silently
absent section in the rendered slide.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from presentation_maker.deck.checks.base import CheckContext, Diagnostic, Severity, check

__all__ = ["asset_missing", "asset_not_web_renderable", "include_missing"]

_NOT_WEB_RENDERABLE = frozenset({".pdf", ".eps", ".ai", ".ps", ".tex"})
_HINT_SEARCH_LIMIT = 2000


@check("asset-missing", Severity.ERROR)
def asset_missing(context: CheckContext) -> Iterator[Diagnostic]:
    """An image path that resolves to nothing. Renders as a broken-image box."""
    for asset in context.deck.assets:
        if asset.resolved is None or asset.resolved.exists():
            continue
        yield Diagnostic(
            rule="asset-missing",
            severity=Severity.ERROR,
            message=f"No file at {asset.raw!r} (looked in {asset.resolved}).",
            hint=_relocation_hint(asset.resolved, context.deck.deck_dir),
            file=asset.origin.file,
            line=asset.origin.line,
            column=asset.origin.column,
            slide_id=asset.slide_id,
            slide_index=asset.slide_index,
        )


@check("asset-not-web-renderable", Severity.ERROR)
def asset_not_web_renderable(context: CheckContext) -> Iterator[Diagnostic]:
    """A file no browser draws in an `<img>`, used as one.

    Only reported when the file exists — otherwise `asset-missing` has already said
    the more useful thing, and two diagnostics for one reference is noise.
    """
    for asset in context.deck.assets:
        if asset.resolved is None or not asset.resolved.exists():
            continue
        suffix = asset.resolved.suffix.lower()
        if suffix not in _NOT_WEB_RENDERABLE:
            continue
        yield Diagnostic(
            rule="asset-not-web-renderable",
            severity=Severity.ERROR,
            message=f"A browser will not draw {suffix} in an image tag: {asset.raw!r}.",
            hint="Export it to .png or .svg and point at that instead.",
            file=asset.origin.file,
            line=asset.origin.line,
            column=asset.origin.column,
            slide_id=asset.slide_id,
            slide_index=asset.slide_index,
        )


@check("include-missing", Severity.ERROR)
def include_missing(context: CheckContext) -> Iterator[Diagnostic]:
    """An `{{< include >}}` naming a file that is not there.

    The shortcode leaves no trace in the output, so the slides it would have
    contributed are simply absent from the deck.
    """
    for include in context.deck.includes:
        if include.resolved is not None and include.resolved.is_file():
            continue
        looked = f" (looked in {include.resolved})" if include.resolved else ""
        yield Diagnostic(
            rule="include-missing",
            severity=Severity.ERROR,
            message=f"No file at {include.raw!r}{looked}.",
            hint=_relocation_hint(include.resolved, context.deck.deck_dir),
            file=include.origin.file,
            line=include.origin.line,
            column=include.origin.column,
        )


def _relocation_hint(target: Path | None, deck_dir: Path) -> str:
    """Point at a same-named file elsewhere in the deck, if there is exactly one.

    Worth the search because the common shape of this bug is a file that moved one
    directory over, where naming the new path turns a report into a fix.
    """
    if target is None:
        return ""
    matches: list[Path] = []
    for index, candidate in enumerate(deck_dir.rglob(target.name)):
        if index > _HINT_SEARCH_LIMIT:
            return ""
        matches.append(candidate)
        if len(matches) > 1:
            return ""
    if not matches:
        return ""
    return f"Did you mean {matches[0].relative_to(deck_dir)}?"
