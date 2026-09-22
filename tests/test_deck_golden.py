"""The acceptance test for the parse layer.

For every deck on this machine, the slide list read from source must equal the slide
list pandoc actually built — same ids, same order, same count. That single assertion
is what licenses the rest of the tooling to answer questions about a deck without
rendering it. `/presentations/` is gitignored, so these only run where decks exist.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from presentation_maker.deck.bridge import to_slide_refs
from presentation_maker.deck.parser import parse_deck

_ROOT = Path(__file__).resolve().parents[1]
_RENDERED = sorted((_ROOT / "presentations").glob("*/index.html"))
_SECTION_ID_RE = re.compile(r'<section[^>]*\bid="([^"]*)"')
_TITLE_SLIDE_ID = "title-slide"

pytestmark = pytest.mark.skipif(not _RENDERED, reason="no rendered decks available")


def _rendered_ids(html_path: Path) -> list[str]:
    return _SECTION_ID_RE.findall(html_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("html_path", _RENDERED, ids=lambda p: p.parent.name)
def test_parsed_slides_equal_the_rendered_deck(html_path: Path) -> None:
    rendered = [i for i in _rendered_ids(html_path) if i != _TITLE_SLIDE_ID]
    parsed = list(parse_deck(html_path.parent / "index.qmd").slide_ids())
    assert parsed == rendered


@pytest.mark.parametrize("html_path", _RENDERED, ids=lambda p: p.parent.name)
def test_slide_refs_match_revealjs_indices(html_path: Path) -> None:
    """`Slide.index` has to be the number `pres shot --slide <n>` takes."""
    rendered = _rendered_ids(html_path)
    refs = to_slide_refs(parse_deck(html_path.parent / "index.qmd"))
    assert [ref.slide_id for ref in refs] == rendered
    assert [ref.index for ref in refs] == list(range(len(rendered)))


@pytest.mark.parametrize("html_path", _RENDERED, ids=lambda p: p.parent.name)
def test_every_local_asset_reference_resolves_inside_the_repo(html_path: Path) -> None:
    """A resolved path escaping the repo means the resolution rules are wrong."""
    model = parse_deck(html_path.parent / "index.qmd")
    for asset in model.assets:
        if asset.resolved is None:
            continue
        assert _ROOT in asset.resolved.parents, f"{asset.raw} resolved to {asset.resolved}"
