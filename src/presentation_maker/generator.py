from __future__ import annotations

import functools
import shutil
from pathlib import Path

from presentation_maker.models import PresentationConfig
from presentation_maker.templates import (
    _PARTIAL_FILENAMES,
    render_index_qmd,
    render_logo_inject_html,
    render_quarto_yml,
)

_ROOT_MARKER = "pyproject.toml"


def find_project_root(start: Path | None = None) -> Path | None:
    """Nearest ancestor of `start` (default: cwd) holding pyproject.toml.

    Returns None rather than raising, so callers that merely want to *ask* — a check
    running against an arbitrary path, a test in tmp_path — do not have to catch.
    `project_root()` is the variant that insists.
    """
    current = (Path.cwd() if start is None else Path(start)).absolute()
    for candidate in (current, *current.parents):
        if (candidate / _ROOT_MARKER).exists():
            return candidate
    return None


@functools.cache
def project_root() -> Path:
    """The project root, or a RuntimeError the CLI knows how to render.

    Resolved lazily and once. Resolving at import time instead made the package
    unimportable from any cwd outside the repo, which is a strange thing for a library
    to do to the programs that depend on it.
    """
    root = find_project_root()
    if root is None:
        raise RuntimeError(
            "Could not find project root. Run 'pres' from within the presentation-maker directory."
        )
    return root


def __getattr__(name: str) -> object:
    """Redirect the removed `PROJECT_ROOT` global to its lazy replacement."""
    if name == "PROJECT_ROOT":
        raise AttributeError(
            "generator.PROJECT_ROOT was removed because it resolved at import time. "
            "Call generator.project_root() instead, or find_project_root(path) to "
            "resolve against something other than the cwd."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_presentations_dir() -> Path:
    return project_root() / "presentations"


def presentation_exists(slug: str) -> bool:
    return (get_presentations_dir() / slug).exists()


def get_posters_dir() -> Path:
    return project_root() / "posters"


def poster_exists(slug: str) -> bool:
    return (get_posters_dir() / slug).exists()


def scaffold_presentation(config: PresentationConfig) -> Path:
    target_dir = get_presentations_dir() / config.slug
    if target_dir.exists():
        raise FileExistsError(
            f"Presentation '{config.slug}' already exists at {target_dir}"
        )
    target_dir.mkdir(parents=True, exist_ok=False)
    _write_file(target_dir / "_quarto.yml", render_quarto_yml(config))
    _write_file(target_dir / "index.qmd", render_index_qmd(config))
    _write_file(target_dir / "logo-inject.html", render_logo_inject_html(config))
    _write_file(target_dir / "styles.scss", "/*-- scss:rules --*/\n")
    _copy_images(target_dir)
    _copy_partials(config, target_dir)
    return target_dir


def _copy_images(target_dir: Path) -> None:
    src = project_root() / "images"
    dst = target_dir / "images"
    if src.exists():
        shutil.copytree(src, dst)


def _copy_partials(config: PresentationConfig, target_dir: Path) -> None:
    partials_src = project_root() / "partials"
    partials_dst = target_dir / "partials"
    partials_dst.mkdir(exist_ok=True)
    for partial_type in config.partials:
        filename = _PARTIAL_FILENAMES[partial_type]
        src_file = partials_src / filename
        if src_file.exists():
            shutil.copy2(src_file, partials_dst / filename)


def list_presentations() -> list[dict[str, str]]:
    pres_dir = get_presentations_dir()
    if not pres_dir.exists():
        return []
    return [
        {
            "slug": child.name,
            "title": _extract_title(child / "index.qmd"),
            "path": str(child),
        }
        for child in sorted(pres_dir.iterdir())
        if (child / "index.qmd").exists()
    ]


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _extract_title(qmd_path: Path) -> str:
    try:
        for line in qmd_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"')
    except OSError:
        pass
    return qmd_path.parent.name
