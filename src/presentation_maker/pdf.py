from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

from presentation_maker.browser import Viewport, open_page

_PDF_WIDTH = "20in"
_PDF_HEIGHT = "11.25in"
_PDF_SCALE = 1.0
_POSTER_WIDTH = "24in"
_POSTER_HEIGHT = "36in"
_POSTER_VIEWPORT_WIDTH = 2304   # 24in at 96dpi
_POSTER_VIEWPORT_HEIGHT = 3456  # 36in at 96dpi
_LOAD_WAIT_MS = 2_000

POSTER_VIEWPORT = Viewport(_POSTER_VIEWPORT_WIDTH, _POSTER_VIEWPORT_HEIGHT)


def export_presentation_pdf(slug: str, pres_dir: Path, project_root: Path) -> Path:
    """Render presentation to PDF; returns path of written file."""
    ensure_html_rendered(pres_dir, project_root)
    output_path = pres_dir / f"{slug}.pdf"
    _export_pdf(pres_dir / "index.html", output_path)
    return output_path


def export_poster_pdf(slug: str, poster_dir: Path, project_root: Path) -> Path:
    """Render poster to 24×36in PDF; returns path of written file."""
    ensure_html_rendered(poster_dir, project_root)
    output_path = poster_dir / f"{slug}.pdf"
    _export_poster_pdf(poster_dir / "index.html", output_path)
    return output_path


def ensure_html_rendered(
    target_dir: Path,
    project_root: Path,
    *,
    force: bool = False,
    quiet: bool = False,
) -> bool:
    """Run `quarto render` if the built HTML is missing or out of date.

    Returns True if a render actually ran. Rendering from the project root is what
    lets the relative image paths inside a deck resolve.
    """
    if not force and not is_html_stale(target_dir, project_root):
        return False
    qmd = target_dir / "index.qmd"
    if not qmd.exists():
        raise FileNotFoundError(f"index.qmd not found in {target_dir}")
    subprocess.run(
        ["quarto", "render", str(qmd)],
        cwd=str(project_root),
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
    )
    return True


def is_html_stale(target_dir: Path, project_root: Path) -> bool:
    """True if index.html is missing or older than anything it is built from.

    Without this check an edit followed by an export silently ships the previous
    build — the exact failure mode that makes an agent believe a change landed
    when it did not.
    """
    html = target_dir / "index.html"
    if not html.exists():
        return True
    built_at = html.stat().st_mtime
    return any(
        source.exists() and source.stat().st_mtime > built_at
        for source in _source_files(target_dir, project_root)
    )


def _source_files(target_dir: Path, project_root: Path) -> Iterator[Path]:
    """Every file whose contents can change the rendered output."""
    for name in ("index.qmd", "_quarto.yml", "styles.scss", "logo-inject.html"):
        yield target_dir / name
    yield from (target_dir / "partials").glob("**/*.qmd")
    yield from (project_root / "styles").glob("*.scss")
    yield from (project_root / "partials").glob("*.qmd")
    yield project_root / "_brand.yml"


def _export_pdf(html_path: Path, output_path: Path) -> None:
    url = f"{html_path.as_uri()}?print-pdf"
    with open_page(url, settle_ms=_LOAD_WAIT_MS) as (page, _diagnostics):
        page.pdf(
            path=str(output_path),
            width=_PDF_WIDTH,
            height=_PDF_HEIGHT,
            print_background=True,
            scale=_PDF_SCALE,
        )


def _export_poster_pdf(html_path: Path, output_path: Path) -> None:
    with open_page(
        html_path.as_uri(),
        viewport=POSTER_VIEWPORT,
        settle_ms=_LOAD_WAIT_MS,
        print_media=True,
    ) as (page, _diagnostics):
        page.pdf(
            path=str(output_path),
            width=_POSTER_WIDTH,
            height=_POSTER_HEIGHT,
            print_background=True,
        )
