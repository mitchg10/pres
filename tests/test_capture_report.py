from __future__ import annotations

from pathlib import Path

from presentation_maker.capture_models import CaptureResult
from presentation_maker.capture_report import (
    REPORT_NAME,
    build_contact_sheet,
    resize_to_width,
    write_report,
)


def _result(tmp_path: Path, **overrides) -> CaptureResult:
    return CaptureResult(slug="my-talk", out_dir=tmp_path, **overrides)


def test_clean_report_says_so_explicitly(tmp_path: Path) -> None:
    report = write_report(_result(tmp_path, images=[tmp_path / "slide-00.png"]), tmp_path / REPORT_NAME)
    text = report.read_text(encoding="utf-8")

    assert "slide-00.png" in text
    assert "No console errors or warnings." in text
    assert "No content escaped a slide." in text


def test_problems_are_listed_with_the_cdn_explanation(tmp_path: Path) -> None:
    result = _result(
        tmp_path,
        overflow=["slide-04.png: content is 120px taller than the slide"],
        failed_requests=["https://cdn.example/fa.css (net::ERR_FAILED)"],
        console_errors=["error: gsap is not defined"],
    )
    text = write_report(result, tmp_path / REPORT_NAME).read_text(encoding="utf-8")

    assert "120px taller" in text
    assert "gsap is not defined" in text
    assert "Font Awesome" in text


def test_contact_sheet_tiles_every_image(tmp_path: Path) -> None:
    from PIL import Image

    images = []
    for index in range(4):
        path = tmp_path / f"slide-0{index}.png"
        Image.new("RGB", (320, 180), (index * 40, 0, 0)).save(path)
        images = [*images, path]

    sheet = build_contact_sheet(images, tmp_path / "contact-sheet.png")

    assert sheet is not None
    with Image.open(sheet) as opened:
        # Four images at three columns means two rows.
        assert opened.width > opened.height / 2


def test_contact_sheet_of_nothing_is_skipped(tmp_path: Path) -> None:
    assert build_contact_sheet([], tmp_path / "contact-sheet.png") is None


def test_resize_shrinks_to_width_and_keeps_the_aspect_ratio(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "poster.png"
    Image.new("RGB", (2304, 3456)).save(path)

    resize_to_width(path, 1152)

    with Image.open(path) as resized:
        assert resized.size == (1152, 1728)


def test_resize_leaves_an_already_small_image_alone(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "small.png"
    Image.new("RGB", (400, 300)).save(path)

    resize_to_width(path, 1152)

    with Image.open(path) as untouched:
        assert untouched.size == (400, 300)
