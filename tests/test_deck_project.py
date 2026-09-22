"""Quarto project discovery and asset-path resolution.

The two rules encoded here were established empirically against rendered decks, and
both are counterintuitive enough to be worth pinning:

1. A leading ``/`` resolves against the *deck* directory, not the repo root, because
   each deck directory has its own ``_quarto.yml`` and is therefore its own project.
2. A relative path written inside a partial resolves against the **including**
   document's directory, because Quarto splices partials in textually.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.deck.project import find_quarto_project, resolve_asset


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    root = tmp_path / "presentations" / "demo"
    (root / "images").mkdir(parents=True)
    (root / "partials").mkdir()
    (root / "_quarto.yml").write_text("project:\n  type: default\n")
    (root / "images" / "ada.jpg").touch()
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "shared.png").touch()
    (tmp_path / "pyproject.toml").touch()
    return root


def test_finds_the_nearest_quarto_project(deck: Path) -> None:
    assert find_quarto_project(deck / "partials") == deck
    assert find_quarto_project(deck / "index.qmd") == deck


def test_no_quarto_project(tmp_path: Path) -> None:
    assert find_quarto_project(tmp_path) is None


def test_absolute_path_resolves_against_the_deck_not_the_repo(deck: Path) -> None:
    resolved = resolve_asset("/images/ada.jpg", document_dir=deck, project_dir=deck)
    assert resolved == deck / "images" / "ada.jpg"


def test_relative_path_resolves_against_the_document(deck: Path) -> None:
    assert resolve_asset("images/ada.jpg", document_dir=deck, project_dir=deck) == (
        deck / "images" / "ada.jpg"
    )
    assert resolve_asset("./images/ada.jpg", document_dir=deck, project_dir=deck) == (
        deck / "images" / "ada.jpg"
    )


def test_partial_relative_path_climbs_from_the_deck(deck: Path) -> None:
    """``../../images/x`` written in a partial is relative to the deck, not the partial."""
    resolved = resolve_asset("../../images/shared.png", document_dir=deck, project_dir=deck)
    assert resolved == deck.parent.parent / "images" / "shared.png"
    assert resolved is not None and resolved.exists()


def test_missing_file_still_resolves_to_a_path(deck: Path) -> None:
    """Resolution and existence are separate questions; the check asks the second."""
    resolved = resolve_asset("images/nope.png", document_dir=deck, project_dir=deck)
    assert resolved == deck / "images" / "nope.png"
    assert not resolved.exists()


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com/a.png",
        "http://example.com/a.png",
        "data:image/png;base64,iVBOR",
        "//cdn.example.com/a.png",
        "",
    ],
)
def test_external_and_empty_targets_do_not_resolve(raw: str, deck: Path) -> None:
    assert resolve_asset(raw, document_dir=deck, project_dir=deck) is None


def test_percent_encoding_is_decoded(deck: Path) -> None:
    (deck / "images" / "IDEEAS_h_wt lockup.png").touch()
    resolved = resolve_asset(
        "images/IDEEAS_h_wt%20lockup.png", document_dir=deck, project_dir=deck
    )
    assert resolved is not None and resolved.exists()


def test_query_and_fragment_are_stripped(deck: Path) -> None:
    resolved = resolve_asset("images/ada.jpg?v=2#top", document_dir=deck, project_dir=deck)
    assert resolved == deck / "images" / "ada.jpg"
