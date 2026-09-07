"""Shared headless-Chromium plumbing for PDF export and screenshot capture.

Playwright is imported lazily inside the functions that need it so that a
missing install still surfaces as the friendly ImportError message the CLI
already prints, rather than breaking `import presentation_maker`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMEOUT_MS = 60_000
REVEAL_READY_TIMEOUT_MS = 15_000


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int
    scale: float = 1.0


class PageDiagnostics:
    """Collects browser-side problems worth reporting back to the caller.

    The decks pull GSAP and Font Awesome from CDNs, so an offline or blocked
    capture silently loses icons and animation — a failed request is often the
    real explanation for a screenshot that "looks wrong".
    """

    def __init__(self) -> None:
        self._console_errors: list[str] = []
        self._failed_requests: list[str] = []

    def attach(self, page: Any) -> None:
        page.on("console", self._record_console)
        page.on("pageerror", self._record_page_error)
        page.on("requestfailed", self._record_failed_request)

    def _record_console(self, message: Any) -> None:
        if message.type in ("error", "warning"):
            self._console_errors.append(f"{message.type}: {message.text}")

    def _record_page_error(self, error: Any) -> None:
        self._console_errors.append(f"pageerror: {error}")

    def _record_failed_request(self, request: Any) -> None:
        failure = getattr(request, "failure", None) or "request failed"
        self._failed_requests.append(f"{request.url} ({failure})")

    @property
    def console_errors(self) -> tuple[str, ...]:
        return tuple(self._console_errors)

    @property
    def failed_requests(self) -> tuple[str, ...]:
        return tuple(self._failed_requests)


@contextmanager
def open_page(
    url: str,
    *,
    viewport: Viewport | None = None,
    settle_ms: int = 0,
    print_media: bool = False,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> Iterator[tuple[Any, PageDiagnostics]]:
    """Open `url` in headless Chromium, yielding the page and its diagnostics."""
    from playwright.sync_api import sync_playwright

    diagnostics = PageDiagnostics()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(**_page_options(viewport))
            diagnostics.attach(page)
            if print_media:
                page.emulate_media(media="print")
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if settle_ms:
                page.wait_for_timeout(settle_ms)
            yield page, diagnostics
        finally:
            browser.close()


def _page_options(viewport: Viewport | None) -> dict[str, Any]:
    if viewport is None:
        return {}
    return {
        "viewport": {"width": viewport.width, "height": viewport.height},
        "device_scale_factor": viewport.scale,
    }


def wait_for_reveal(page: Any, timeout_ms: int = REVEAL_READY_TIMEOUT_MS) -> bool:
    """Block until reveal.js reports ready; return False if it never does.

    Worth waiting for beyond page load: `logo-inject.html` rewrites the slide
    logo on `Reveal.on('ready')`, so capturing earlier can miss it.
    """
    from playwright.sync_api import Error as PlaywrightError

    try:
        page.wait_for_function(
            "() => Boolean(window.Reveal && window.Reveal.isReady && window.Reveal.isReady())",
            timeout=timeout_ms,
        )
        return True
    except PlaywrightError:
        return False
