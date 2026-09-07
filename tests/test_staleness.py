"""The staleness check is what stops an export from silently shipping the
previous build after an edit — the failure mode that makes a screenshot lie."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from presentation_maker.pdf import is_html_stale

_EARLIER = 1_700_000_000
_LATER = _EARLIER + 60


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    """A minimal project root containing one rendered presentation."""
    target = tmp_path / "presentations" / "my-talk"
    (target / "partials").mkdir(parents=True)
    (tmp_path / "styles").mkdir()
    (tmp_path / "partials").mkdir()

    _write(target / "index.qmd", _EARLIER)
    _write(target / "_quarto.yml", _EARLIER)
    _write(target / "styles.scss", _EARLIER)
    _write(target / "partials" / "_extra.qmd", _EARLIER)
    _write(tmp_path / "styles" / "components.scss", _EARLIER)
    _write(tmp_path / "partials" / "_agenda.qmd", _EARLIER)
    _write(tmp_path / "_brand.yml", _EARLIER)
    _write(target / "index.html", _LATER)
    return target


def _write(path: Path, mtime: float) -> None:
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_fresh_build_is_not_stale(deck: Path) -> None:
    assert is_html_stale(deck, deck.parent.parent) is False


def test_missing_html_is_stale(deck: Path) -> None:
    (deck / "index.html").unlink()
    assert is_html_stale(deck, deck.parent.parent) is True


@pytest.mark.parametrize(
    "source",
    ["index.qmd", "_quarto.yml", "styles.scss", "partials/_extra.qmd"],
)
def test_edited_deck_source_makes_the_build_stale(deck: Path, source: str) -> None:
    _write(deck / source, _LATER + 60)
    assert is_html_stale(deck, deck.parent.parent) is True


@pytest.mark.parametrize(
    "source",
    ["styles/components.scss", "partials/_agenda.qmd", "_brand.yml"],
)
def test_edited_shared_source_makes_the_build_stale(deck: Path, source: str) -> None:
    """Shared styling lives outside the deck, but still changes what it renders."""
    project_root = deck.parent.parent
    _write(project_root / source, _LATER + 60)
    assert is_html_stale(deck, project_root) is True


def test_missing_optional_sources_are_ignored(deck: Path) -> None:
    """A deck without partials or a logo injection is not perpetually stale."""
    (deck / "partials" / "_extra.qmd").unlink()
    (deck / "partials").rmdir()
    assert is_html_stale(deck, deck.parent.parent) is False
