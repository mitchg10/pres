"""``{{< include >}}`` expansion.

Quarto splices partials in textually, so expansion produces a flat line stream. Each
line keeps the file and line number it was *written* at, which is what lets a
diagnostic about a partial point at the partial.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.deck.includes import CircularIncludeError, expand_includes


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    (tmp_path / "partials").mkdir()
    return tmp_path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_a_deck_without_includes_is_its_own_lines(deck: Path) -> None:
    source = _write(deck / "index.qmd", "## One\n\ntext\n")
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["## One", "", "text"]
    assert [line.origin.line for line in lines] == [1, 2, 3]
    assert all(line.origin.file == source for line in lines)
    assert all(line.depth == 0 for line in lines)
    assert includes == ()


def test_an_include_is_spliced_at_its_position(deck: Path) -> None:
    _write(deck / "partials" / "_agenda.qmd", "## Agenda\n\n1. Thing\n")
    source = _write(deck / "index.qmd", "## One\n\n{{< include partials/_agenda.qmd >}}\n\n## Two\n")

    lines, includes = expand_includes(source)

    assert [line.text for line in lines] == ["## One", "", "## Agenda", "", "1. Thing", "", "## Two"]
    assert len(includes) == 1
    assert includes[0].raw == "partials/_agenda.qmd"
    assert includes[0].resolved == deck / "partials" / "_agenda.qmd"
    assert includes[0].origin.line == 3


def test_included_lines_keep_their_own_file_and_line(deck: Path) -> None:
    partial = _write(deck / "partials" / "_agenda.qmd", "## Agenda\n\n1. Thing\n")
    source = _write(deck / "index.qmd", "## One\n\n{{< include partials/_agenda.qmd >}}\n")

    lines, _ = expand_includes(source)
    agenda = next(line for line in lines if line.text == "## Agenda")

    assert agenda.origin.file == partial
    assert agenda.origin.line == 1, "line 1 of the partial, not line 3 of the deck"
    assert agenda.depth == 1


def test_includes_resolve_relative_to_the_file_holding_them(deck: Path) -> None:
    """A nested include is relative to the partial, not to the deck."""
    _write(deck / "partials" / "nested" / "_deep.qmd", "deep\n")
    _write(deck / "partials" / "_outer.qmd", "{{< include nested/_deep.qmd >}}\n")
    source = _write(deck / "index.qmd", "{{< include partials/_outer.qmd >}}\n")

    lines, includes = expand_includes(source)

    assert [line.text for line in lines] == ["deep"]
    assert lines[0].depth == 2
    assert len(includes) == 2


def test_an_include_can_climb_above_the_deck(deck: Path) -> None:
    _write(deck.parent / "shared" / "_thanks.qmd", "## Thanks\n")
    source = _write(deck / "index.qmd", "{{< include ../shared/_thanks.qmd >}}\n")
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["## Thanks"]
    assert includes[0].resolved == deck.parent / "shared" / "_thanks.qmd"


def test_a_missing_include_is_recorded_not_raised(deck: Path) -> None:
    """The path it looked for is kept, so the diagnostic can say where it looked."""
    source = _write(deck / "index.qmd", "## One\n{{< include partials/_gone.qmd >}}\n")
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["## One"]
    assert includes[0].resolved == deck / "partials" / "_gone.qmd"
    assert not includes[0].resolved.exists()


def test_quoted_include_paths(deck: Path) -> None:
    _write(deck / "partials" / "a b.qmd", "spaced\n")
    source = _write(deck / "index.qmd", '{{< include "partials/a b.qmd" >}}\n')
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["spaced"]
    assert includes[0].raw == "partials/a b.qmd"


def test_a_cycle_raises(deck: Path) -> None:
    _write(deck / "partials" / "_a.qmd", "{{< include _b.qmd >}}\n")
    _write(deck / "partials" / "_b.qmd", "{{< include _a.qmd >}}\n")
    source = _write(deck / "index.qmd", "{{< include partials/_a.qmd >}}\n")
    with pytest.raises(CircularIncludeError, match="_a.qmd"):
        expand_includes(source)


def test_the_same_partial_twice_is_not_a_cycle(deck: Path) -> None:
    _write(deck / "partials" / "_a.qmd", "a\n")
    source = _write(
        deck / "index.qmd",
        "{{< include partials/_a.qmd >}}\n{{< include partials/_a.qmd >}}\n",
    )
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["a", "a"]
    assert len(includes) == 2


def test_a_commented_out_include_is_not_expanded(deck: Path) -> None:
    """Authors park slides inside HTML comments; an include in there is inert."""
    _write(deck / "partials" / "_a.qmd", "## Real\n")
    source = _write(deck / "index.qmd", "<!-- {{< include partials/_a.qmd >}} -->\n## Kept\n")
    lines, includes = expand_includes(source)
    assert [line.text for line in lines] == ["", "## Kept"]
    assert includes == ()


def test_a_multi_line_comment_keeps_the_line_count(deck: Path) -> None:
    """Blanking rather than deleting is what keeps every later origin.line honest."""
    source = _write(deck / "index.qmd", "## A\n<!-- ## Parked\n\ncontent\n-->\n## B\n")
    lines, _ = expand_includes(source)
    assert [line.text for line in lines] == ["## A", "", "", "", "", "## B"]
    assert [line.origin.line for line in lines] == [1, 2, 3, 4, 5, 6]
