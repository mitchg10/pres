"""Models describing a screenshot capture request and its result."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

# The deck is authored at 1920x1080 (see templates.render_quarto_yml), but reveal
# scales its content to whatever viewport it is given, so a smaller viewport is
# still a faithful picture of the layout — just a cheaper image for an agent to
# read back. Full resolution is one --width/--height away.
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_WAIT_MS = 1200
DEFAULT_INTERVAL_MS = 400


class SlideRef(BaseModel):
    """A slide in a rendered deck, as reveal.js sees it."""

    index: int
    """Zero-based horizontal index — matches the `#/N` hash (hashOneBasedIndex is false)."""

    slide_id: str = ""
    """Slug of the `##` heading, e.g. `the-failure-categories`. Stable across edits."""


class CaptureOptions(BaseModel):
    """Everything the capture engine needs beyond which presentation to shoot."""

    slides: str = "all"
    """Selector: `all`, an index, a slide id, a `2-5` range, or a comma-separated mix."""

    fragments: bool = False
    frames: Annotated[int, Field(ge=0, le=60)] = 0
    interval_ms: Annotated[int, Field(ge=0)] = DEFAULT_INTERVAL_MS
    contact_sheet: bool = False
    out_dir: Path | None = None
    width: Annotated[int, Field(gt=0)] = DEFAULT_WIDTH
    height: Annotated[int, Field(gt=0)] = DEFAULT_HEIGHT
    scale: Annotated[float, Field(gt=0, le=4)] = 1.0
    wait_ms: Annotated[int, Field(ge=0)] = DEFAULT_WAIT_MS
    render: bool = True
    """Re-run `quarto render` when the built HTML is older than its sources."""

    url: str | None = None
    """Capture from a running `quarto preview` instead of the rendered file:// build."""

    report: bool = True

    quiet: bool = False
    """Silence quarto's render output, so `--json` stdout stays parseable."""


class CaptureResult(BaseModel):
    """What a capture produced, and anything that looked wrong while producing it."""

    slug: str
    out_dir: Path
    images: list[Path] = Field(default_factory=list)
    contact_sheet: Path | None = None
    report: Path | None = None
    console_errors: list[str] = Field(default_factory=list)
    failed_requests: list[str] = Field(default_factory=list)
    overflow: list[str] = Field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.console_errors or self.failed_requests or self.overflow)
