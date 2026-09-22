"""Project-root resolution.

The point of these tests is that resolution is *lazy and parameterized*. It used to
happen at import time against the process cwd, which made `presentation_maker`
unimportable from anywhere outside the repo — including from pytest's tmp_path, and
including from any future library code that wants to analyze a deck by path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from presentation_maker import generator


def _make_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    return root


def test_finds_root_from_the_root_itself(tmp_path: Path) -> None:
    _make_project(tmp_path)
    assert generator.find_project_root(tmp_path) == tmp_path


def test_finds_root_from_a_nested_directory(tmp_path: Path) -> None:
    _make_project(tmp_path)
    nested = tmp_path / "presentations" / "some-deck" / "partials"
    nested.mkdir(parents=True)
    assert generator.find_project_root(nested) == tmp_path


def test_finds_nearest_root_when_projects_nest(tmp_path: Path) -> None:
    _make_project(tmp_path)
    inner = _make_project(tmp_path / "vendored")
    assert generator.find_project_root(inner) == inner


def test_returns_none_when_there_is_no_project(tmp_path: Path) -> None:
    """A miss is a value, not an exception — callers decide whether it is fatal."""
    assert generator.find_project_root(tmp_path) is None


def test_defaults_to_the_current_directory(tmp_path: Path, monkeypatch) -> None:
    _make_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert generator.find_project_root() == tmp_path


def test_project_root_raises_a_readable_error_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    generator.project_root.cache_clear()
    with pytest.raises(RuntimeError, match="presentation-maker"):
        generator.project_root()
    generator.project_root.cache_clear()


def test_project_root_is_cached(monkeypatch) -> None:
    generator.project_root.cache_clear()
    first = generator.project_root()
    calls: list[Path | None] = []

    def _spy(start: Path | None = None) -> Path | None:
        calls.append(start)
        return first

    monkeypatch.setattr(generator, "find_project_root", _spy)
    assert generator.project_root() == first
    assert calls == [], "project_root() should not re-resolve on every call"


def test_removed_project_root_global_points_at_its_replacement() -> None:
    """A stale `generator.PROJECT_ROOT` should say what to use, not just 404."""
    with pytest.raises(AttributeError, match="project_root"):
        generator.PROJECT_ROOT


def test_importing_from_outside_a_project_does_not_raise(tmp_path: Path) -> None:
    """The regression this phase exists to prevent."""
    import subprocess
    import sys

    src = Path(__file__).resolve().parent.parent / "src"
    result = subprocess.run(
        [sys.executable, "-c", "import presentation_maker.generator; print('ok')"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(src), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
