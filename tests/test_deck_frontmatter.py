"""Splitting the YAML header off a .qmd."""

from __future__ import annotations

from presentation_maker.deck.frontmatter import split_frontmatter

DECK = '''---
title: "It's Like 'X'"
date: "2026-06-23"
title-slide-attributes:
  data-background-color: "#861F41"
---

## First Slide
'''


def test_reads_the_header() -> None:
    meta, offset = split_frontmatter(DECK)
    assert meta["title"] == "It's Like 'X'"
    assert meta["title-slide-attributes"] == {"data-background-color": "#861F41"}
    assert offset == 6, "body starts on line 7, so six lines were consumed"


def test_no_header_consumes_nothing() -> None:
    assert split_frontmatter("## Only A Slide\n") == ({}, 0)


def test_a_horizontal_rule_is_not_a_header() -> None:
    """``---`` has to be the very first line to open a header."""
    assert split_frontmatter("Some prose\n\n---\n\nMore prose\n") == ({}, 0)


def test_unterminated_header_is_not_a_header() -> None:
    meta, offset = split_frontmatter("---\ntitle: x\n\n## Slide\n")
    assert (meta, offset) == ({}, 0)


def test_empty_header() -> None:
    assert split_frontmatter("---\n---\n## Slide\n") == ({}, 2)


def test_malformed_yaml_is_not_fatal() -> None:
    """A checker that crashes on a bad header cannot report the bad header."""
    meta, offset = split_frontmatter("---\ntitle: [unclosed\n---\n## Slide\n")
    assert meta == {}
    assert offset == 3
