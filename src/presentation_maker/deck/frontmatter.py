"""Splitting the YAML header off a .qmd document."""

from __future__ import annotations

from typing import Any

import yaml

__all__ = ["split_frontmatter"]

_FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict[str, Any], int]:
    """Return the parsed header and the number of lines it occupied.

    The line count is the point: everything downstream reports positions in the
    original file, so the body has to know how far into it the body starts.

    A header that does not open on line 1, never closes, or does not parse yields
    ``({}, ...)`` rather than raising — the job here is to keep going so that the
    checks can report the real problem, and a deck with a broken header is exactly
    when a checker is most useful.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FENCE:
        return {}, 0

    for offset, line in enumerate(lines[1:], start=1):
        if line.strip() != _FENCE:
            continue
        consumed = offset + 1
        try:
            parsed = yaml.safe_load("\n".join(lines[1:offset]))
        except yaml.YAMLError:
            return {}, consumed
        return (parsed if isinstance(parsed, dict) else {}), consumed

    return {}, 0
