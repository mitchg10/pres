"""Turning a deck's source into a `DeckModel`, without rendering it.

Orchestration only — the hard parts live in `includes`, `frontmatter`, `attrs`,
`identifiers`, and `project`. The order matters: frontmatter is read from the deck's
own file, includes are expanded so that partial content lands at its include position,
and only then are headings counted. Doing it in any other order gets the slide list
wrong, which is the one thing this module exists to get right.
"""

from __future__ import annotations

import re
from pathlib import Path

from presentation_maker.deck.attrs import parse_attrs, split_trailing_attrs
from presentation_maker.deck.frontmatter import split_frontmatter
from presentation_maker.deck.identifiers import disambiguate, heading_to_id
from presentation_maker.deck.includes import expand_includes
from presentation_maker.deck.models import AssetRef, DeckModel, Slide, SourceLine, SourcePos
from presentation_maker.deck.project import find_quarto_project, resolve_asset

__all__ = ["parse_deck"]

_SLIDE_HEADING_RE = re.compile(r"^##(?!#)\s*(.*)$")
_CODE_FENCE_RE = re.compile(r"^\s*(?:`{3,}|~{3,})")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
_HTML_IMAGE_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*\"([^\"]*)\"")
_BACKGROUND_KEYS = ("background-image", "data-background-image")


def parse_deck(source: Path, *, slug: str | None = None) -> DeckModel:
    """Parse the deck whose entry document is `source` (normally `index.qmd`)."""
    deck_dir = source.parent
    project_dir = find_quarto_project(deck_dir) or deck_dir
    metadata, header_lines = split_frontmatter(source.read_text(encoding="utf-8"))
    lines, includes = expand_includes(source)
    body = _drop_header(lines, source=source, header_lines=header_lines)

    has_title_slide = bool(metadata.get("title"))
    slides = _read_slides(body, index_offset=1 if has_title_slide else 0)
    assets = _read_assets(
        body, slides=slides, document_dir=deck_dir, project_dir=project_dir
    )

    return DeckModel(
        slug=slug or deck_dir.name,
        deck_dir=deck_dir,
        source=source,
        frontmatter=metadata,
        slides=slides,
        includes=includes,
        assets=assets,
        has_title_slide=has_title_slide,
    )


def _drop_header(
    lines: tuple[SourceLine, ...], *, source: Path, header_lines: int
) -> tuple[SourceLine, ...]:
    if not header_lines:
        return lines
    return tuple(
        line
        for line in lines
        if not (line.origin.file == source and line.origin.line <= header_lines)
    )


def _read_slides(
    lines: tuple[SourceLine, ...], *, index_offset: int
) -> tuple[Slide, ...]:
    """Every `##` heading outside a code fence becomes one slide.

    `index_offset` is 1 when Quarto will generate a title slide ahead of them, so that
    `Slide.index` is the index reveal — and therefore `pres shot --slide` — will use.
    """
    starts = tuple(_heading_positions(lines))
    raw = tuple(_heading_text(lines[position]) for position in starts)
    base_ids = tuple(heading_to_id(text) for text in raw)
    ids = disambiguate(base_ids)

    slides: list[Slide] = []
    for index, (position, text, slide_id) in enumerate(zip(starts, raw, ids)):
        heading, block = split_trailing_attrs(text)
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        slides.append(
            Slide(
                index=index + index_offset,
                slide_id=slide_id,
                base_id=base_ids[index],
                heading=heading,
                attrs=parse_attrs(block),
                origin=lines[position].origin,
                body=lines[position + 1 : end],
            )
        )
    return tuple(slides)


def _heading_positions(lines: tuple[SourceLine, ...]) -> list[int]:
    return [
        position
        for position, line in _outside_code_fences(lines)
        if _SLIDE_HEADING_RE.match(line.text)
    ]


def _heading_text(line: SourceLine) -> str:
    match = _SLIDE_HEADING_RE.match(line.text)
    assert match is not None
    return match.group(1).strip().rstrip("#").strip()


def _outside_code_fences(
    lines: tuple[SourceLine, ...],
) -> list[tuple[int, SourceLine]]:
    """Positions of the lines pandoc reads as markdown rather than as code."""
    kept: list[tuple[int, SourceLine]] = []
    in_code = False
    for position, line in enumerate(lines):
        if _CODE_FENCE_RE.match(line.text):
            in_code = not in_code
            continue
        if not in_code:
            kept.append((position, line))
    return kept


def _read_assets(
    lines: tuple[SourceLine, ...],
    *,
    slides: tuple[Slide, ...],
    document_dir: Path,
    project_dir: Path,
) -> tuple[AssetRef, ...]:
    owner = _slide_owner(lines, slides)
    assets: list[AssetRef] = []

    for position, line in _outside_code_fences(lines):
        index, slide_id = owner[position]
        for raw, column in _asset_targets(line.text):
            assets.append(
                AssetRef(
                    raw=raw,
                    resolved=resolve_asset(
                        raw, document_dir=document_dir, project_dir=project_dir
                    ),
                    origin=SourcePos(
                        file=line.origin.file, line=line.origin.line, column=column
                    ),
                    slide_index=index,
                    slide_id=slide_id,
                )
            )
    return tuple(assets)


def _asset_targets(text: str) -> list[tuple[str, int]]:
    """Every local-file reference on a line, with its 1-based column."""
    found = [
        (match.group(1), match.start(1) + 1)
        for pattern in (_MARKDOWN_IMAGE_RE, _HTML_IMAGE_RE)
        for match in pattern.finditer(text)
    ]
    _, block = split_trailing_attrs(text)
    if block:
        attrs = parse_attrs(block)
        for key in _BACKGROUND_KEYS:
            value = attrs.get(key)
            if value:
                found.append((value, text.find(value) + 1))
    return found


def _slide_owner(
    lines: tuple[SourceLine, ...], slides: tuple[Slide, ...]
) -> list[tuple[int | None, str]]:
    """For each line position, the slide it belongs to — None before the first one."""
    owner: list[tuple[int | None, str]] = [(None, "")] * len(lines)
    boundaries = [
        next(p for p, line in enumerate(lines) if line.origin == slide.origin)
        for slide in slides
    ]
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else len(lines)
        for position in range(start, end):
            owner[position] = (slides[index].index, slides[index].slide_id)
    return owner
