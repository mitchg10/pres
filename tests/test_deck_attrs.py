"""Pandoc attribute blocks: ``{#id .class key="value"}``.

One parser serves headings, fenced divs, and image attribute blocks, so the cases here
are drawn from all three. The quoting rules are the whole difficulty: a `}` or a space
inside a quoted value does not end anything.
"""

from __future__ import annotations

import pytest

from presentation_maker.deck.attrs import parse_attrs, split_trailing_attrs
from presentation_maker.deck.models import PandocAttrs


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ("", PandocAttrs()),
        ("{}", PandocAttrs()),
        ("{#my-id}", PandocAttrs(identifier="my-id")),
        ("{.columns}", PandocAttrs(classes=("columns",))),
        ("{.fragment .fade-up}", PandocAttrs(classes=("fragment", "fade-up"))),
        (
            '{.column width="38%"}',
            PandocAttrs(classes=("column",), keyvals=(("width", "38%"),)),
        ),
        (
            '{background-color="#861F41"}',
            PandocAttrs(keyvals=(("background-color", "#861F41"),)),
        ),
        (
            '{#hero .card--maroon data-x="1" .big}',
            PandocAttrs(
                identifier="hero",
                classes=("card--maroon", "big"),
                keyvals=(("data-x", "1"),),
            ),
        ),
        # A brace and a space inside a quoted value are literal.
        (
            '{style="width: 100%; box-shadow: 0 4px 16px rgba(0,0,0,0.3);"}',
            PandocAttrs(keyvals=(("style", "width: 100%; box-shadow: 0 4px 16px rgba(0,0,0,0.3);"),)),
        ),
        (
            '{fig-alt="A {curly} caption" .plain}',
            PandocAttrs(classes=("plain",), keyvals=(("fig-alt", "A {curly} caption"),)),
        ),
        # Single quotes are quotes too, and a backslash escapes one.
        ("{title='It\\'s fine'}", PandocAttrs(keyvals=(("title", "It's fine"),))),
        ("{title='two words'}", PandocAttrs(keyvals=(("title", "two words"),))),
        # A bare word is neither class nor key; pandoc keeps it as a valueless key.
        ("{unnumbered}", PandocAttrs(keyvals=(("unnumbered", ""),))),
    ],
)
def test_parse_attrs(block: str, expected: PandocAttrs) -> None:
    assert parse_attrs(block) == expected


def test_parse_attrs_accepts_a_block_without_braces() -> None:
    """Callers that already stripped the braces should not have to add them back."""
    assert parse_attrs('.column width="38%"') == PandocAttrs(
        classes=("column",), keyvals=(("width", "38%"),)
    )


def test_last_id_wins_like_pandoc() -> None:
    assert parse_attrs("{#first #second}").identifier == "second"


@pytest.mark.parametrize(
    ("line", "text", "block"),
    [
        ("## Plain Heading", "## Plain Heading", ""),
        ('## Ada Mandate {background-color="#861F41"}', "## Ada Mandate", 'background-color="#861F41"'),
        ("::: {.fragment}", ":::", ".fragment"),
        # A brace in a quoted value must not be read as the start of the block.
        ('## T {fig-alt="a { b"}', "## T", 'fig-alt="a { b"'),
        # Unbalanced: not an attribute block at all.
        ("## Set notation }", "## Set notation }", ""),
    ],
)
def test_split_trailing_attrs(line: str, text: str, block: str) -> None:
    assert split_trailing_attrs(line) == (text, block)


def test_pandoc_attrs_get_and_has_class() -> None:
    attrs = parse_attrs('{.card--maroon width="38%"}')
    assert attrs.has_class("card--maroon")
    assert not attrs.has_class("card--gold")
    assert attrs.get("width") == "38%"
    assert attrs.get("height") is None
    assert attrs.get("height", "auto") == "auto"


def test_pandoc_attrs_is_hashable() -> None:
    """Frozen means frozen — these end up in sets when checks dedupe."""
    assert len({parse_attrs("{.a}"), parse_attrs("{.a}"), parse_attrs("{.b}")}) == 2
