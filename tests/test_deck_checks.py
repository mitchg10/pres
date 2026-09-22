"""The check rules and the runner that drives them."""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.deck.checks import REGISTRY, Severity, run_checks
from presentation_maker.deck.checks.base import CheckContext, Diagnostic
from presentation_maker.deck.parser import parse_deck

HEADER = '---\ntitle: "A Deck"\n---\n\n'


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    (root / "images").mkdir(parents=True)
    (root / "partials").mkdir()
    (root / "_quarto.yml").write_text("project:\n  type: default\n")
    (root / "images" / "ada.jpg").touch()
    return root


def _check(deck: Path, body: str, *, build: str | None = None) -> tuple[Diagnostic, ...]:
    source = deck / "index.qmd"
    source.write_text(HEADER + body)
    if build is not None:
        (deck / "index.html").write_text(build)
    return run_checks(parse_deck(source), build_dir=deck if build is not None else None)


def _rules(diagnostics: tuple[Diagnostic, ...]) -> list[str]:
    return [diagnostic.rule for diagnostic in diagnostics]


# --- slide-id-duplicate -------------------------------------------------------


def test_duplicate_slide_ids_are_reported(deck: Path) -> None:
    found = _check(deck, "## Learn it\n\n## Learn it\n")
    assert _rules(found) == ["slide-id-duplicate"]
    diagnostic = found[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.slide_index == 2, "the second heading is the one to fix"
    assert diagnostic.slide_id == "learn-it-1"
    assert "learn-it" in diagnostic.message
    assert diagnostic.line == 7


def test_three_way_collision_reports_each_later_heading(deck: Path) -> None:
    found = _check(deck, "## A\n\n## A\n\n## A\n")
    assert _rules(found) == ["slide-id-duplicate"] * 2


def test_distinct_headings_are_clean(deck: Path) -> None:
    assert _check(deck, "## First\n\n## Second\n") == ()


def test_an_explicit_id_resolves_a_collision(deck: Path) -> None:
    assert _check(deck, "## Learn it\n\n## Learn it {#learn-it-again}\n") == ()


# --- asset-missing / asset-not-web-renderable ---------------------------------


def test_a_missing_asset_is_reported(deck: Path) -> None:
    found = _check(deck, "## First\n\n![](images/gone.png)\n")
    assert _rules(found) == ["asset-missing"]
    assert found[0].slide_index == 1
    assert "images/gone.png" in found[0].message


def test_a_present_asset_is_clean(deck: Path) -> None:
    assert _check(deck, "## First\n\n![](images/ada.jpg)\n") == ()


def test_a_remote_asset_is_not_checked(deck: Path) -> None:
    assert _check(deck, "## First\n\n![](https://example.com/a.png)\n") == ()


def test_a_near_miss_gets_a_hint(deck: Path) -> None:
    """Two of the bugs this rule was written for had the file one directory over."""
    (deck / "figures").mkdir()
    (deck / "figures" / "chart.png").touch()
    found = _check(deck, "## First\n\n![](images/chart.png)\n")
    assert _rules(found) == ["asset-missing"]
    assert "figures/chart.png" in found[0].hint


def test_no_hint_when_nothing_matches(deck: Path) -> None:
    found = _check(deck, "## First\n\n![](images/nowhere.png)\n")
    assert found[0].hint == ""


def test_a_pdf_used_as_an_image_is_reported(deck: Path) -> None:
    (deck / "images" / "fig.pdf").touch()
    found = _check(deck, "## First\n\n![](images/fig.pdf)\n")
    assert _rules(found) == ["asset-not-web-renderable"]
    assert ".pdf" in found[0].message


def test_a_missing_pdf_is_reported_once_not_twice(deck: Path) -> None:
    """One broken reference should produce one diagnostic, not a pile."""
    assert _rules(_check(deck, "## First\n\n![](images/gone.pdf)\n")) == ["asset-missing"]


# --- include-missing ----------------------------------------------------------


def test_a_missing_include_is_reported(deck: Path) -> None:
    found = _check(deck, "## First\n\n{{< include partials/_gone.qmd >}}\n")
    assert _rules(found) == ["include-missing"]
    assert "partials/_gone.qmd" in found[0].message
    assert found[0].line == 7


def test_a_present_include_is_clean(deck: Path) -> None:
    (deck / "partials" / "_a.qmd").write_text("## Agenda\n")
    assert _check(deck, "## First\n\n{{< include partials/_a.qmd >}}\n") == ()


# --- slide-id-drift -----------------------------------------------------------


def _build(*ids: str) -> str:
    sections = "".join(f'<section id="{i}"></section>' for i in ("title-slide", *ids))
    return f"<html><body>{sections}</body></html>"


def test_drift_is_silent_when_the_build_agrees(deck: Path) -> None:
    assert _check(deck, "## First\n\n## Second\n", build=_build("first", "second")) == ()


def test_drift_is_reported_when_the_build_disagrees(deck: Path) -> None:
    found = _check(deck, "## First\n\n## Second\n", build=_build("first", "different"))
    assert _rules(found) == ["slide-id-drift"]
    assert found[0].severity is Severity.WARNING
    assert "different" in found[0].message


def test_drift_is_skipped_without_a_build(deck: Path) -> None:
    assert _check(deck, "## First\n\n## Nope\n") == ()


# --- the runner ---------------------------------------------------------------


def test_diagnostics_come_back_in_source_order(deck: Path) -> None:
    body = "## A\n\n![](images/gone.png)\n\n## A\n\n{{< include partials/_gone.qmd >}}\n"
    found = _check(deck, body)
    assert [diagnostic.line for diagnostic in found] == sorted(d.line for d in found)


def test_a_failing_check_does_not_kill_the_run(deck: Path) -> None:
    """One bad rule must not cost the report every other rule's findings."""

    def exploding(context: CheckContext):
        raise ZeroDivisionError("boom")

    exploding.rule = "exploding"
    exploding.severity = Severity.ERROR

    source = deck / "index.qmd"
    source.write_text(HEADER + "## A\n\n![](images/gone.png)\n")
    found = run_checks(parse_deck(source), checks=(*REGISTRY, exploding))

    assert "asset-missing" in _rules(found)
    assert "internal-error" in _rules(found)
    assert "boom" in next(d for d in found if d.rule == "internal-error").message


def test_rules_can_be_selected_and_ignored(deck: Path) -> None:
    body = "## A\n\n## A\n\n![](images/gone.png)\n"
    source = deck / "index.qmd"
    source.write_text(HEADER + body)
    model = parse_deck(source)

    assert set(_rules(run_checks(model, only=("asset-missing",)))) == {"asset-missing"}
    assert "asset-missing" not in _rules(run_checks(model, ignore=("asset-missing",)))


def test_every_registered_rule_has_a_unique_name() -> None:
    names = [check.rule for check in REGISTRY]
    assert len(names) == len(set(names))
    assert "internal-error" not in names, "reserved for the runner"
