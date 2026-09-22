"""Pandoc-fidelity tests for heading -> slide id conversion.

The cases below are not invented: each one is a heading that appears in a real
deck, paired with the id pandoc actually emitted for it. They were harvested by
comparing every ``##`` heading against the ``<section id=...>`` in the deck's
rendered ``index.html``.
"""

import re
from pathlib import Path

import pytest

from presentation_maker.deck.identifiers import disambiguate, heading_to_id

# Headings where the old naive rule (`[^a-z0-9]+` -> `-`) disagreed with pandoc.
# 20 cases across 6 decks, every one a `pres shot --slide <id>` that used to fail.
PANDOC_CASES = [
    # Leading digits are dropped entirely (step 5 is isalpha, not isalnum).
    ("1975: A Defense Software Crisis", "a-defense-software-crisis"),
    # A literal hyphen survives alongside the hyphens made from its spaces.
    ("Results - Dimensions of AI Understanding", "results---dimensions-of-ai-understanding"),
    # Apostrophes and quotes are deleted, not hyphenated.
    ('"Before We Start, Let Me Check That We\'re Recording"',
     "before-we-start-let-me-check-that-were-recording"),
    ("DEX's Three Techniques", "dexs-three-techniques"),
    ("What I Couldn't Reproduce", "what-i-couldnt-reproduce"),
    ("Stress Testing DEX's Assumptions", "stress-testing-dexs-assumptions"),
    ("Why We're Doing This (and Why It Feels Uncomfortable)",
     "why-were-doing-this-and-why-it-feels-uncomfortable"),
    ("Beginner's Mind, Expert's Mind", "beginners-mind-experts-mind"),
    ('Why It\'s "Stupid"', "why-its-stupid"),
    # Ampersand is deleted, so Q&A collapses to qa.
    ("Case 2: LLM Q&A", "case-2-llm-qa"),
    # A period survives -- pandoc keeps `-`, `_` and `.`.
    ("Paper vs. CloudLab: Hardware", "paper-vs.-cloudlab-hardware"),
    ("Benchmark Parameters: Paper vs. CloudLab", "benchmark-parameters-paper-vs.-cloudlab"),
    ("AISI vs. Main Track: Which One?", "aisi-vs.-main-track-which-one"),
    ("AAAI-27 vs. EAAI-27: At a Glance", "aaai-27-vs.-eaai-27-at-a-glance"),
    ("This vs. MDPI Paper: The Same Failure", "this-vs.-mdpi-paper-the-same-failure"),
    # Non-ASCII letters survive, lowercased. An ASCII class would delete them.
    ("Surprisal à la Katz", "surprisal-à-la-katz"),
    ("Why Δ Is Local", "why-δ-is-local"),
    ("Calibrating λ: High-Precision Recovery", "calibrating-λ-high-precision-recovery"),
    ("Cost-Sensitive λ", "cost-sensitive-λ"),
    ("Assumption #1: Propose, Don't Detect", "assumption-1-propose-dont-detect"),
]


@pytest.mark.parametrize(("heading", "expected"), PANDOC_CASES)
def test_matches_pandoc(heading, expected):
    assert heading_to_id(heading) == expected


ATTRIBUTE_CASES = [
    ("Paper vs. CloudLab: Hardware {.smaller}", "paper-vs.-cloudlab-hardware"),
    ('Case 2: LLM Q&A {background-color="#508590"}', "case-2-llm-qa"),
    ("Thank You {.center .conclusion}", "thank-you"),
    # An explicit id wins verbatim and is never slugified.
    ("The Results {#results-2024}", "results-2024"),
    ('Divider {#my_ID .chaos background-color="#861F41"}', "my_ID"),
]


@pytest.mark.parametrize(("heading", "expected"), ATTRIBUTE_CASES)
def test_strips_attributes_and_honors_explicit_id(heading, expected):
    assert heading_to_id(heading) == expected


EDGE_CASES = [
    ("Runs   of    whitespace", "runs-of-whitespace"),
    ("  leading and trailing  ", "leading-and-trailing"),
    ("snake_case.and.dots", "snake_case.and.dots"),
    ("!!!", "section"),
    ("", "section"),
    ("123", "section"),
    ("2026 Roadmap", "roadmap"),
    ("---", "section"),
]


@pytest.mark.parametrize(("heading", "expected"), EDGE_CASES)
def test_edge_cases(heading, expected):
    assert heading_to_id(heading) == expected


def test_disambiguate_suffixes_collisions_in_document_order():
    ids = ("intro", "body", "intro", "intro", "body")
    assert disambiguate(ids) == ("intro", "body", "intro-1", "intro-2", "body-1")


def test_disambiguate_leaves_unique_ids_alone():
    ids = ("a", "b", "c")
    assert disambiguate(ids) == ids


def test_disambiguate_is_empty_safe():
    assert disambiguate(()) == ()


# --- Golden fixtures against real rendered decks -------------------------------
# `/presentations/` is gitignored, so these only run on a machine that has decks.

_ROOT = Path(__file__).resolve().parents[1]
_RENDERED = sorted((_ROOT / "presentations").glob("*/index.html"))
_HEADING_RE = re.compile(r"^##\s+(?!#)(.*)$", re.MULTILINE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _source_headings(qmd: str) -> list[str]:
    """Headings that pandoc will actually turn into slides.

    Commented-out headings must be dropped first: authors park whole slides
    inside ``<!-- ... -->`` (``cs-6204-dex/index.qmd:264-390`` hides three), and
    counting them is the classic false positive in this codebase.
    """
    return _HEADING_RE.findall(_HTML_COMMENT_RE.sub("", qmd))


@pytest.mark.skipif(not _RENDERED, reason="no rendered decks available")
@pytest.mark.parametrize("html_path", _RENDERED, ids=lambda p: p.parent.name)
def test_every_source_heading_matches_a_rendered_section(html_path):
    """Every id we compute must exist in the deck pandoc actually built."""
    rendered = set(re.findall(r'<section id="([^"]+)"', html_path.read_text()))
    qmd = (html_path.parent / "index.qmd").read_text()
    computed = [heading_to_id(h) for h in _source_headings(qmd)]
    # Collisions are disambiguated by pandoc, so compare the disambiguated form.
    unknown = [i for i in disambiguate(computed) if i not in rendered]
    assert not unknown, f"computed ids absent from the render: {unknown}"
