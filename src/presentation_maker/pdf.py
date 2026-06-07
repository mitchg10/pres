from __future__ import annotations

import subprocess
from pathlib import Path

_PDF_WIDTH = "20in"
_PDF_HEIGHT = "11.25in"
_PDF_SCALE = 1.0
_POSTER_WIDTH = "24in"
_POSTER_HEIGHT = "36in"
_POSTER_VIEWPORT_WIDTH = 2304   # 24in at 96dpi
_POSTER_VIEWPORT_HEIGHT = 3456  # 36in at 96dpi
_LOAD_WAIT_MS = 2_000
_TIMEOUT_MS = 60_000


def export_presentation_pdf(slug: str, pres_dir: Path, project_root: Path) -> Path:
    """Render presentation to PDF; returns path of written file."""
    _ensure_html_rendered(pres_dir, project_root)
    output_path = pres_dir / f"{slug}.pdf"
    _export_pdf(pres_dir / "index.html", output_path)
    return output_path


def export_poster_pdf(slug: str, poster_dir: Path, project_root: Path) -> Path:
    """Render poster to 24×36in PDF; returns path of written file."""
    _ensure_html_rendered(poster_dir, project_root)
    output_path = poster_dir / f"{slug}.pdf"
    _export_poster_pdf(poster_dir / "index.html", output_path)
    return output_path


def _ensure_html_rendered(target_dir: Path, project_root: Path) -> None:
    if (target_dir / "index.html").exists():
        return
    qmd = target_dir / "index.qmd"
    if not qmd.exists():
        raise FileNotFoundError(f"index.qmd not found in {target_dir}")
    subprocess.run(
        ["quarto", "render", str(qmd)],
        cwd=str(project_root),
        check=True,
    )


def _export_pdf(html_path: Path, output_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    url = f"file://{html_path}?print-pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=_TIMEOUT_MS)
        page.wait_for_timeout(_LOAD_WAIT_MS)
        page.pdf(
            path=str(output_path),
            width=_PDF_WIDTH,
            height=_PDF_HEIGHT,
            print_background=True,
            scale=_PDF_SCALE,
        )
        browser.close()


def _export_poster_pdf(html_path: Path, output_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    url = f"file://{html_path}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": _POSTER_VIEWPORT_WIDTH, "height": _POSTER_VIEWPORT_HEIGHT}
        )
        page.emulate_media(media="print")
        page.goto(url, wait_until="networkidle", timeout=_TIMEOUT_MS)
        page.wait_for_timeout(_LOAD_WAIT_MS)
        page.pdf(
            path=str(output_path),
            width=_POSTER_WIDTH,
            height=_POSTER_HEIGHT,
            print_background=True,
        )
        browser.close()
