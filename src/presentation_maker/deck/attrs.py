"""Parsing pandoc attribute blocks — ``{#id .class key="value"}``.

Headings, fenced divs, and image attribute blocks all use this syntax, so they all use
this parser. The lexing primitives live in `identifiers`, which is stdlib-only; this
module adds the structure on top.
"""

from __future__ import annotations

from presentation_maker.deck.identifiers import split_trailing_attrs, tokenize_attributes
from presentation_maker.deck.models import PandocAttrs

__all__ = ["parse_attrs", "split_trailing_attrs"]


def parse_attrs(block: str) -> PandocAttrs:
    """Parse an attribute block, with or without its surrounding braces.

    A later `#id` overrides an earlier one, matching pandoc. A bare word with no `.`
    and no `=` becomes a valueless key rather than a class — also pandoc's reading.
    """
    inner = _strip_braces(block.strip())
    identifier = ""
    classes: list[str] = []
    keyvals: list[tuple[str, str]] = []

    for token in tokenize_attributes(inner):
        if token.startswith("#"):
            identifier = token[1:]
        elif token.startswith("."):
            classes.append(token[1:])
        else:
            key, _, value = token.partition("=")
            keyvals.append((key, _unquote(value)))

    return PandocAttrs(
        identifier=identifier,
        classes=tuple(classes),
        keyvals=tuple(keyvals),
    )


def _strip_braces(text: str) -> str:
    if text.startswith("{") and text.endswith("}"):
        return text[1:-1]
    return text


def _unquote(value: str) -> str:
    """Drop surrounding quotes and undo backslash escapes inside them."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return _unescape(value[1:-1])
    return value


def _unescape(value: str) -> str:
    if "\\" not in value:
        return value
    out: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            out.append(char)
    if escaped:
        out.append("\\")
    return "".join(out)
