"""A standalone export has two ways to be quietly wrong: it can be rendered from
the wrong directory (producing a file with reveal.js missing) or it can leave the
chalkboard plugin on (which Quarto refuses outright). Both live in the argv and
the profile, so both are cheap to pin down here."""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker.export import (
    _PROFILE_CONTENT,
    _PROFILE_FILENAME,
    STANDALONE_SUFFIX,
    _build_render_command,
    export_standalone_html,
    standalone_output_path,
)


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    target = tmp_path / "presentations" / "my-talk"
    target.mkdir(parents=True)
    (target / "index.qmd").write_text("---\ntitle: Talk\n---\n", encoding="utf-8")
    return target


def test_command_selects_the_embed_profile(deck: Path) -> None:
    """The profile is the only thing that turns chalkboard off; -M cannot."""
    cmd = _build_render_command(deck / "index.qmd", "my-talk-standalone.html")
    assert "--profile" in cmd
    assert cmd[cmd.index("--profile") + 1] == _PROFILE_FILENAME.removeprefix(
        "_quarto-"
    ).removesuffix(".yml")


def test_profile_disables_chalkboard_and_embeds() -> None:
    assert "embed-resources: true" in _PROFILE_CONTENT
    assert "chalkboard: false" in _PROFILE_CONTENT


def test_command_uses_a_bare_input_name(deck: Path) -> None:
    """Quarto runs with cwd=deck, so the input and output stay relative to it."""
    cmd = _build_render_command(deck / "index.qmd", "my-talk-standalone.html")
    assert cmd[:3] == ["quarto", "render", "index.qmd"]
    assert cmd[cmd.index("--output") + 1] == "my-talk-standalone.html"


def test_default_output_sits_beside_the_deck(deck: Path) -> None:
    assert standalone_output_path("my-talk", deck) == deck / f"my-talk{STANDALONE_SUFFIX}"


def test_explicit_output_is_resolved_to_an_absolute_path(deck: Path, tmp_path: Path) -> None:
    resolved = standalone_output_path("my-talk", deck, tmp_path / "out" / "deck.html")
    assert resolved.is_absolute()
    assert resolved.name == "deck.html"


def test_missing_qmd_is_reported(deck: Path) -> None:
    (deck / "index.qmd").unlink()
    with pytest.raises(FileNotFoundError, match="index.qmd not found"):
        export_standalone_html("my-talk", deck)


def test_a_stray_profile_file_is_not_clobbered(deck: Path) -> None:
    """The profile is written then deleted, so an existing one must stop the run."""
    (deck / _PROFILE_FILENAME).write_text("mine\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_standalone_html("my-talk", deck)
    assert (deck / _PROFILE_FILENAME).read_text(encoding="utf-8") == "mine\n"
