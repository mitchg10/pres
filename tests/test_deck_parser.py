"""Parsing a deck's source into slides, assets, and includes."""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.deck.bridge import to_slide_refs
from presentation_maker.deck.parser import parse_deck
from presentation_maker.slide_selector import parse_slide_selector

HEADER = '---\ntitle: "A Deck"\n---\n\n'


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    (root / "images").mkdir(parents=True)
    (root / "partials").mkdir()
    (root / "_quarto.yml").write_text("project:\n  type: default\n")
    (root / "images" / "ada.jpg").touch()
    return root


def _write(deck: Path, body: str, *, header: str = HEADER) -> Path:
    source = deck / "index.qmd"
    source.write_text(header + body)
    return source


def test_headings_become_slides(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\ntext\n\n## Second\n"))
    assert model.slide_ids() == ("first", "second")
    assert model.slug == "demo"
    assert model.frontmatter["title"] == "A Deck"


def test_slide_index_leaves_room_for_the_title_slide(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\n## Second\n"))
    assert [slide.index for slide in model.slides] == [1, 2]
    assert model.has_title_slide


def test_without_a_title_there_is_no_title_slide(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n", header="---\nauthor: X\n---\n\n"))
    assert not model.has_title_slide
    assert [slide.index for slide in model.slides] == [0]


def test_explicit_id_and_attributes_on_a_heading(deck: Path) -> None:
    model = parse_deck(_write(deck, '## The Ada Mandate {#ada background-color="#861F41"}\n'))
    slide = model.slides[0]
    assert slide.slide_id == "ada"
    assert slide.heading == "The Ada Mandate"
    assert slide.attrs.get("background-color") == "#861F41"


def test_duplicate_headings_are_disambiguated_like_pandoc(deck: Path) -> None:
    model = parse_deck(_write(deck, "## Learn it\n\n## Learn it\n\n## Learn it\n"))
    assert model.slide_ids() == ("learn-it", "learn-it-1", "learn-it-2")


def test_deeper_headings_are_not_slides(deck: Path) -> None:
    model = parse_deck(_write(deck, "## Real\n\n### Sub\n\n#### Deeper\n"))
    assert model.slide_ids() == ("real",)


def test_headings_inside_a_code_fence_are_not_slides(deck: Path) -> None:
    model = parse_deck(_write(deck, "## Real\n\n```python\n## not a slide\n```\n\n## Also Real\n"))
    assert model.slide_ids() == ("real", "also-real")


def test_headings_inside_an_html_comment_are_not_slides(deck: Path) -> None:
    """Whole slides get parked in comments; counting them is the classic false hit."""
    model = parse_deck(_write(deck, "## Real\n\n<!-- ## Parked\n\ncontent\n-->\n\n## Also Real\n"))
    assert model.slide_ids() == ("real", "also-real")


def test_slide_body_stops_at_the_next_heading(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\nalpha\n\n## Second\n\nbeta\n"))
    assert [line.text for line in model.slides[0].body if line.text] == ["alpha"]
    assert [line.text for line in model.slides[1].body if line.text] == ["beta"]


def test_an_include_contributes_slides_at_its_position(deck: Path) -> None:
    (deck / "partials" / "_agenda.qmd").write_text("## Agenda\n\n1. Thing\n")
    model = parse_deck(_write(deck, "## First\n\n{{< include partials/_agenda.qmd >}}\n\n## Last\n"))
    assert model.slide_ids() == ("first", "agenda", "last")
    assert model.slides[1].origin.file == deck / "partials" / "_agenda.qmd"
    assert model.slides[1].origin.line == 1


def test_assets_are_collected_with_their_slide(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\n![Ada](images/ada.jpg)\n"))
    asset = model.assets[0]
    assert asset.raw == "images/ada.jpg"
    assert asset.resolved == deck / "images" / "ada.jpg"
    assert (asset.slide_index, asset.slide_id) == (1, "first")
    assert asset.origin.line == 7


def test_an_absolute_asset_path_resolves_against_the_deck(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\n![Ada](/images/ada.jpg)\n"))
    assert model.assets[0].resolved == deck / "images" / "ada.jpg"


def test_an_asset_inside_a_comment_is_not_collected(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\n<!-- ![](images/gone.png) -->\n"))
    assert model.assets == ()


def test_remote_assets_are_not_resolved(deck: Path) -> None:
    model = parse_deck(_write(deck, "## First\n\n![](https://example.com/a.png)\n"))
    assert model.assets[0].resolved is None
    assert model.assets[0].is_external


def test_html_and_background_images_are_collected(deck: Path) -> None:
    body = '## First {background-image="images/ada.jpg"}\n\n<img src="images/ada.jpg">\n'
    model = parse_deck(_write(deck, body))
    assert [asset.raw for asset in model.assets] == ["images/ada.jpg", "images/ada.jpg"]


def test_a_deck_with_no_slides_parses(deck: Path) -> None:
    model = parse_deck(_write(deck, "just prose\n"))
    assert model.slides == ()


def test_bridge_feeds_the_slide_selector(deck: Path) -> None:
    """The point of the bridge: validate `--slide` without rendering anything."""
    model = parse_deck(_write(deck, "## First\n\n## Second\n"))
    refs = to_slide_refs(model)

    assert [(ref.index, ref.slide_id) for ref in refs] == [
        (0, "title-slide"),
        (1, "first"),
        (2, "second"),
    ]
    assert parse_slide_selector("second", refs) == (2,)
    assert parse_slide_selector("all", refs) == (0, 1, 2)
    with pytest.raises(ValueError, match="nope"):
        parse_slide_selector("nope", refs)
