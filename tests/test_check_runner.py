"""Deck discovery, report assembly, and the exit-code contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.check_models import CheckReport
from presentation_maker.check_runner import (
    DeckNotFoundError,
    check_decks,
    exit_code,
    find_decks,
)
from presentation_maker.deck.checks import Severity

HEADER = '---\ntitle: "A Deck"\n---\n\n'


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    presentations = tmp_path / "presentations"
    for slug, body in (("clean", "## First\n\n## Second\n"), ("broken", "## A\n\n## A\n")):
        deck = presentations / slug
        deck.mkdir(parents=True)
        (deck / "_quarto.yml").write_text("project:\n  type: default\n")
        (deck / "index.qmd").write_text(HEADER + body)
    return presentations


def test_finds_every_deck_when_none_named(tree: Path) -> None:
    assert [p.parent.name for p in find_decks(tree)] == ["broken", "clean"]


def test_finds_named_decks_in_the_order_given(tree: Path) -> None:
    assert [p.parent.name for p in find_decks(tree, ["clean", "broken"])] == [
        "clean",
        "broken",
    ]


def test_an_unknown_name_is_an_error(tree: Path) -> None:
    with pytest.raises(DeckNotFoundError, match="nope"):
        find_decks(tree, ["nope"])


def test_a_missing_tree_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(DeckNotFoundError):
        find_decks(tmp_path / "absent")


def test_an_empty_tree_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "presentations").mkdir()
    with pytest.raises(DeckNotFoundError, match="No presentations found"):
        find_decks(tmp_path / "presentations")


def test_report_carries_slides_for_every_deck(tree: Path) -> None:
    report = check_decks(find_decks(tree), use_build=False)
    by_slug = {deck.slug: deck for deck in report.decks}
    assert [s.slide_id for s in by_slug["clean"].slides] == ["first", "second"]
    assert [s.index for s in by_slug["clean"].slides] == [1, 2]
    assert by_slug["clean"].diagnostics == ()
    assert [d.rule for d in by_slug["broken"].diagnostics] == ["slide-id-duplicate"]


def test_counts_roll_up_across_decks(tree: Path) -> None:
    report = check_decks(find_decks(tree), use_build=False)
    assert report.error_count == 1
    assert report.warning_count == 0


def test_severity_floor_filters(tree: Path) -> None:
    report = check_decks(find_decks(tree), use_build=False, minimum=Severity.ERROR)
    assert report.error_count == 1
    report = check_decks(find_decks(tree), use_build=False, ignore=("slide-id-duplicate",))
    assert report.diagnostics == ()


def test_exit_code_is_zero_when_clean() -> None:
    assert exit_code(CheckReport()) == 0


def test_exit_code_is_one_on_an_error(tree: Path) -> None:
    assert exit_code(check_decks(find_decks(tree), use_build=False)) == 1


def test_warnings_pass_unless_strict(tmp_path: Path) -> None:
    """`--strict` is the only thing that makes a warning fail the run."""
    deck = tmp_path / "presentations" / "drifted"
    deck.mkdir(parents=True)
    (deck / "_quarto.yml").write_text("project:\n  type: default\n")
    (deck / "index.qmd").write_text(HEADER + "## First\n")
    (deck / "index.html").write_text('<section id="title-slide"></section><section id="stale"></section>')

    report = check_decks(find_decks(tmp_path / "presentations"))
    assert [d.rule for d in report.diagnostics] == ["slide-id-drift"]
    assert exit_code(report) == 0
    assert exit_code(report, strict=True) == 1
