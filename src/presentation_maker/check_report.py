"""Rendering a `CheckReport` — for a person, for a machine, and for a matcher.

Three formats because there are three readers. `rich` is for a human at a terminal,
`compact` is `file:line:col: severity rule message` for the VS Code problem matcher
and for grep, and the markdown form is what gets appended to `capture-report.md`.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from presentation_maker.check_models import CheckReport
from presentation_maker.deck.checks import Diagnostic, Severity

__all__ = ["render_compact", "render_console", "render_markdown", "summarize"]

_STYLES = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
}


def render_compact(report: CheckReport) -> str:
    """One line per diagnostic, in the shape the problem matcher parses.

    Keep this boring. The regex on the other end is not clever.
    """
    return "\n".join(diagnostic.compact() for diagnostic in report.diagnostics)


def render_markdown(report: CheckReport) -> str:
    if not report.diagnostics:
        return "## Source checks\n\nNo problems found.\n"

    lines = ["## Source checks", ""]
    for deck in report.decks:
        if not deck.diagnostics:
            continue
        lines.append(f"### {deck.slug}")
        lines.append("")
        for diagnostic in deck.diagnostics:
            lines.append(f"- {_markdown_entry(diagnostic)}")
        lines.append("")
    return "\n".join(lines)


def _markdown_entry(diagnostic: Diagnostic) -> str:
    parts = [
        f"**{diagnostic.severity.value}** `{diagnostic.rule}` "
        f"— {diagnostic.message} (`{diagnostic.file}:{diagnostic.line}`)"
    ]
    if diagnostic.slide_id:
        parts.append(f" Slide `{diagnostic.slide_id}` (index {diagnostic.slide_index}).")
    if diagnostic.hint:
        parts.append(f" {diagnostic.hint}")
    return "".join(parts)


def render_console(report: CheckReport, console: Console) -> None:
    for deck in report.decks:
        if not deck.diagnostics:
            continue
        table = Table(title=deck.slug, title_justify="left", show_lines=False)
        table.add_column("where", style="dim", no_wrap=True)
        table.add_column("rule")
        table.add_column("slide", no_wrap=True)
        table.add_column("problem", overflow="fold")
        for diagnostic in deck.diagnostics:
            table.add_row(
                f"{diagnostic.file.name}:{diagnostic.line}",
                f"[{_STYLES[diagnostic.severity]}]{diagnostic.rule}[/]",
                diagnostic.slide_id or "-",
                _problem_text(diagnostic),
            )
        console.print(table)


def _problem_text(diagnostic: Diagnostic) -> str:
    if not diagnostic.hint:
        return diagnostic.message
    return f"{diagnostic.message}\n[dim]{diagnostic.hint}[/dim]"


def summarize(report: CheckReport) -> str:
    """The one line worth printing when everything else is quiet."""
    decks = len(report.decks)
    noun = "deck" if decks == 1 else "decks"
    if not report.diagnostics:
        return f"No problems found in {decks} {noun}."
    return (
        f"{report.error_count} error(s), {report.warning_count} warning(s) "
        f"in {decks} {noun}."
    )
