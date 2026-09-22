"""Tests for the filesystem/URL slug used as a deck directory name.

This is deliberately *not* the same rule as ``deck.identifiers.heading_to_id``:
a pandoc slide id may contain ``.`` and non-ASCII letters, both of which make
poor directory names. See ``safe_slug``'s docstring.
"""

import pytest
from pydantic import ValidationError

from presentation_maker.models import safe_slug

CASES = [
    ("My Presentation", "my-presentation"),
    # Runs collapse -- the old implementations left "hello---world" here.
    ("Hello - World", "hello-world"),
    ("Already-Slugged", "already-slugged"),
    ("cs-6204-dex", "cs-6204-dex"),
    ("  padded  ", "padded"),
    ("Lots!!! of??? punctuation", "lots-of-punctuation"),
    ("Trailing dashes --", "trailing-dashes"),
    ("2026 Roadmap", "2026-roadmap"),
    ("under_scores", "under-scores"),
    ("dots.in.name", "dots-in-name"),
]


@pytest.mark.parametrize(("raw", "expected"), CASES)
def test_safe_slug(raw, expected):
    assert safe_slug(raw) == expected


def test_safe_slug_is_idempotent():
    for raw, _ in CASES:
        once = safe_slug(raw)
        assert safe_slug(once) == once


@pytest.mark.parametrize("raw", ["", "   ", "!!!", "---"])
def test_safe_slug_yields_empty_when_nothing_survives(raw):
    assert safe_slug(raw) == ""


def test_presentation_config_rejects_an_unsalvageable_slug():
    from datetime import date

    from presentation_maker.models import DepartmentType, PresentationConfig

    with pytest.raises(ValidationError):
        PresentationConfig(
            title="T",
            subtitle="S",
            author="A",
            date=date(2026, 1, 1),
            slug="!!!",
            department=DepartmentType.CS,
            partials=[],
            slides=[],
        )
