"""Expanding ``{{< include ... >}}`` into a flat stream of source lines.

Quarto splices partials in textually, so the output is simply the deck's lines with
each include replaced by the lines of the file it names. Two things make it more than
a string substitution:

* every line carries the file and line number it was **written** at, so a diagnostic
  about a partial points at the partial rather than at wherever it landed; and
* HTML comments are blanked first. Authors park whole slides inside ``<!-- ... -->``
  (`cs-6204-dex/index.qmd` hides three that way), and counting those as content is the
  classic false positive in this codebase. They are blanked rather than deleted so
  that every later line keeps its real line number.
"""

from __future__ import annotations

import re
from pathlib import Path

from presentation_maker.deck.models import IncludeRef, SourceLine, SourcePos

__all__ = ["CircularIncludeError", "expand_includes"]

_INCLUDE_RE = re.compile(r"^\{\{<\s*include\s+(.+?)\s*>\}\}$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_MAX_DEPTH = 32


class CircularIncludeError(RuntimeError):
    """An include chain that returns to a file already being expanded."""


def expand_includes(source: Path) -> tuple[tuple[SourceLine, ...], tuple[IncludeRef, ...]]:
    """Expand `source` and everything it includes, depth-first, in document order."""
    lines: list[SourceLine] = []
    includes: list[IncludeRef] = []
    _expand_into(source, lines, includes, stack=(), depth=0)
    return tuple(lines), tuple(includes)


def _expand_into(
    source: Path,
    lines: list[SourceLine],
    includes: list[IncludeRef],
    *,
    stack: tuple[Path, ...],
    depth: int,
) -> None:
    key = _key(source)
    if key in stack:
        chain = " -> ".join(path.name for path in (*stack, key))
        raise CircularIncludeError(f"Circular include: {chain}")
    if depth > _MAX_DEPTH:
        raise CircularIncludeError(f"Include nesting deeper than {_MAX_DEPTH}: {source}")

    for number, text in enumerate(_read_lines(source), start=1):
        origin = SourcePos(file=source, line=number)
        target = _include_target(text)
        if target is None:
            lines.append(SourceLine(text=text, origin=origin, depth=depth))
            continue

        resolved = _resolve_include(target, source)
        includes.append(IncludeRef(raw=target, resolved=resolved, origin=origin))
        if resolved is None or not resolved.is_file():
            continue
        _expand_into(resolved, lines, includes, stack=(*stack, key), depth=depth + 1)


def _read_lines(source: Path) -> list[str]:
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise OSError(f"Could not read {source}: {error}") from error
    return _blank_comments(text).splitlines()


def _blank_comments(text: str) -> str:
    return _HTML_COMMENT_RE.sub(lambda match: "\n" * match.group(0).count("\n"), text)


def _include_target(text: str) -> str | None:
    """The path in a standalone include shortcode, or None.

    Only a shortcode occupying a whole line splices; that is how every deck here
    writes them, and it keeps a shortcode mentioned inside prose from being followed.
    """
    match = _INCLUDE_RE.match(text.strip())
    if match is None:
        return None
    return _unquote(match.group(1))


def _resolve_include(target: str, source: Path) -> Path | None:
    """Includes resolve against the file holding them, not against the deck root."""
    if not target:
        return None
    return Path(_normpath(source.parent / target))


def _normpath(path: Path) -> str:
    import os.path

    return os.path.normpath(path)


def _key(source: Path) -> Path:
    return Path(_normpath(source.absolute()))


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value
