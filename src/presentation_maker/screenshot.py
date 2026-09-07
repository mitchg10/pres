"""Capture PNGs of rendered slides and posters.

This exists so an agent (or a person) can look at a change instead of guessing:
edit the source, run a capture, open the image. Mirrors the shape of `pdf.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from presentation_maker import pdf, reveal
from presentation_maker.browser import Viewport, open_page, wait_for_reveal
from presentation_maker.capture_models import CaptureOptions, CaptureResult, SlideRef
from presentation_maker.capture_naming import (
    fragment_filename,
    frame_filename,
    slide_filename,
)
from presentation_maker.capture_report import (
    CONTACT_SHEET_NAME,
    REPORT_NAME,
    build_contact_sheet,
    resize_to_width,
    write_report,
)
from presentation_maker.slide_selector import parse_slide_selector

# Reveal's slide transition is 'slide' (see templates.render_quarto_yml); this is
# long enough for it to finish before the shutter, without padding every capture.
_TRANSITION_MS = 400
_FRAGMENT_MS = 250
_POSTER_NAME = "poster.png"


def capture_presentation(
    slug: str,
    pres_dir: Path,
    project_root: Path,
    options: CaptureOptions,
) -> CaptureResult:
    """Screenshot the selected slides of a deck; returns what was written."""
    out_dir = _prepare_out_dir(slug, project_root, options)
    url = _resolve_url(pres_dir, project_root, options)

    with open_page(
        url,
        viewport=Viewport(options.width, options.height, options.scale),
        settle_ms=options.wait_ms,
    ) as (page, diagnostics):
        if not wait_for_reveal(page):
            raise RuntimeError(
                f"reveal.js never became ready at {url}. If the deck was rendered "
                "recently, check that index_files/ sits beside index.html."
            )
        slides = reveal.list_slides(page)
        indices = parse_slide_selector(options.slides, slides)
        images, overflow = _capture_slides(page, slides, indices, out_dir, options)

    return _finalize(
        CaptureResult(
            slug=slug,
            out_dir=out_dir,
            images=list(images),
            console_errors=list(diagnostics.console_errors),
            failed_requests=list(diagnostics.failed_requests),
            overflow=list(overflow),
        ),
        options,
    )


def capture_poster(
    slug: str,
    poster_dir: Path,
    project_root: Path,
    options: CaptureOptions,
) -> CaptureResult:
    """Screenshot a poster as one full-page PNG, scaled down to the asked-for width."""
    out_dir = _prepare_out_dir(slug, project_root, options)
    url = _resolve_url(poster_dir, project_root, options)
    viewport = Viewport(options.width, options.height, options.scale)

    with open_page(url, viewport=viewport, settle_ms=options.wait_ms) as (page, diagnostics):
        output = out_dir / _POSTER_NAME
        page.screenshot(path=str(output), full_page=True)
        resize_to_width(output, options.width)

    return _finalize(
        CaptureResult(
            slug=slug,
            out_dir=out_dir,
            images=[output],
            console_errors=list(diagnostics.console_errors),
            failed_requests=list(diagnostics.failed_requests),
        ),
        options,
    )


def _capture_slides(
    page: Any,
    slides: tuple[SlideRef, ...],
    indices: tuple[int, ...],
    out_dir: Path,
    options: CaptureOptions,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    images: tuple[Path, ...] = ()
    overflow: tuple[str, ...] = ()

    for index in indices:
        slide = slides[index]
        if options.fragments:
            captured = _capture_fragment_steps(page, slide, out_dir)
        elif options.frames:
            captured = _capture_frames(page, slide, out_dir, options)
        else:
            captured = (_capture_final_state(page, slide, out_dir),)

        images = (*images, *captured)
        problem = reveal.measure_overflow(page)
        if problem:
            overflow = (*overflow, f"{slide_filename(slide)}: {problem}")

    return images, overflow


def _capture_final_state(page: Any, slide: SlideRef, out_dir: Path) -> Path:
    """The slide with every fragment revealed — all of its content in one image."""
    reveal.goto_slide(page, slide.index, settle_ms=_TRANSITION_MS)
    steps = reveal.count_fragment_steps(page)
    if steps:
        reveal.goto_slide(page, slide.index, fragment=steps - 1, settle_ms=_FRAGMENT_MS)
    return _shoot(page, out_dir / slide_filename(slide))


def _capture_fragment_steps(page: Any, slide: SlideRef, out_dir: Path) -> tuple[Path, ...]:
    """One image per reveal step, starting from nothing revealed.

    Needed because the decks render with `pdfSeparateFragments: false`, so the
    PDF export flattens fragments to their final state and intermediate reveals
    are otherwise invisible.
    """
    reveal.goto_slide(page, slide.index, settle_ms=_TRANSITION_MS)
    steps = reveal.count_fragment_steps(page)

    captured: tuple[Path, ...] = ()
    for step in range(steps + 1):
        reveal.goto_slide(
            page,
            slide.index,
            fragment=step - 1,
            settle_ms=_FRAGMENT_MS if step else 0,
        )
        captured = (*captured, _shoot(page, out_dir / fragment_filename(slide, step)))
    return captured


def _capture_frames(
    page: Any,
    slide: SlideRef,
    out_dir: Path,
    options: CaptureOptions,
) -> tuple[Path, ...]:
    """A time series on one slide, for animations a single still cannot show."""
    reveal.goto_slide(page, slide.index)

    captured: tuple[Path, ...] = ()
    elapsed = 0
    for frame in range(options.frames):
        if frame:
            page.wait_for_timeout(options.interval_ms)
            elapsed += options.interval_ms
        captured = (*captured, _shoot(page, out_dir / frame_filename(slide, elapsed)))
    return captured


def _shoot(page: Any, path: Path) -> Path:
    page.screenshot(path=str(path))
    return path


def _finalize(result: CaptureResult, options: CaptureOptions) -> CaptureResult:
    """Write the optional contact sheet and report, folding them into the result."""
    sheet = None
    if options.contact_sheet:
        sheet = build_contact_sheet(result.images, result.out_dir / CONTACT_SHEET_NAME)

    completed = result.model_copy(update={"contact_sheet": sheet})
    if not options.report:
        return completed
    report_path = write_report(completed, completed.out_dir / REPORT_NAME)
    return completed.model_copy(update={"report": report_path})


def _prepare_out_dir(slug: str, project_root: Path, options: CaptureOptions) -> Path:
    out_dir = options.out_dir or project_root / "build" / "shots" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _resolve_url(target_dir: Path, project_root: Path, options: CaptureOptions) -> str:
    """Prefer an already-running preview; otherwise render and read the file."""
    if options.url:
        return options.url
    if options.render:
        pdf.ensure_html_rendered(target_dir, project_root, quiet=options.quiet)
    html = target_dir / "index.html"
    if not html.exists():
        raise FileNotFoundError(
            f"{html} does not exist. Drop --no-render, or run 'quarto render' first."
        )
    return html.as_uri()
