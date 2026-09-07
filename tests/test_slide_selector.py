from __future__ import annotations

import pytest

from presentation_maker.capture_models import SlideRef
from presentation_maker.slide_selector import parse_slide_selector

SLIDES = (
    SlideRef(index=0, slide_id="title-slide"),
    SlideRef(index=1, slide_id="agenda"),
    SlideRef(index=2, slide_id="the-stress-test"),
    SlideRef(index=3, slide_id="how-it-works"),
    SlideRef(index=4, slide_id=""),
)


@pytest.mark.parametrize("selector", ["all", "ALL", "", "   "])
def test_all_forms_select_every_slide(selector: str) -> None:
    assert parse_slide_selector(selector, SLIDES) == (0, 1, 2, 3, 4)


def test_single_index() -> None:
    assert parse_slide_selector("3", SLIDES) == (3,)


def test_slide_id() -> None:
    assert parse_slide_selector("the-stress-test", SLIDES) == (2,)


def test_slide_id_is_case_insensitive_and_accepts_hash_prefix() -> None:
    assert parse_slide_selector("#/The-Stress-Test", SLIDES) == (2,)


def test_inclusive_range() -> None:
    assert parse_slide_selector("1-3", SLIDES) == (1, 2, 3)


def test_reversed_range_is_normalized() -> None:
    assert parse_slide_selector("3-1", SLIDES) == (1, 2, 3)


def test_range_is_clipped_to_the_deck() -> None:
    assert parse_slide_selector("3-99", SLIDES) == (3, 4)


def test_comma_separated_mix_preserves_order() -> None:
    assert parse_slide_selector("3, agenda, 0", SLIDES) == (3, 1, 0)


def test_duplicates_are_dropped() -> None:
    assert parse_slide_selector("2,2,1,2", SLIDES) == (2, 1)


def test_hyphenated_slide_id_is_not_read_as_a_range() -> None:
    """`how-it-works` must resolve as an id, not as a numeric range."""
    assert parse_slide_selector("how-it-works", SLIDES) == (3,)


def test_out_of_range_index_names_the_valid_range() -> None:
    with pytest.raises(ValueError, match="valid indices 0-4"):
        parse_slide_selector("9", SLIDES)


def test_unknown_id_lists_the_available_ids() -> None:
    with pytest.raises(ValueError, match="agenda"):
        parse_slide_selector("nonexistent-slide", SLIDES)


def test_range_entirely_outside_the_deck_is_rejected() -> None:
    with pytest.raises(ValueError, match="did not name any slide"):
        parse_slide_selector("20-30", SLIDES)


def test_empty_deck_is_rejected() -> None:
    with pytest.raises(ValueError, match="no slides"):
        parse_slide_selector("all", ())
