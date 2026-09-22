from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator



def safe_slug(value: str) -> str:
    """Return a slug safe to use as a directory name and a URL path segment.

    Collapses every run of non-alphanumeric characters to a single hyphen and
    trims the ends, so ``"Hello - World"`` becomes ``hello-world`` rather than
    ``hello---world``. Returns ``""`` when nothing survives; callers that need a
    non-empty result are responsible for rejecting it.

    This is *not* the rule for slide ids. Pandoc keeps ``.``, ``_`` and
    non-ASCII letters in a heading id, all of which are unwelcome in a path --
    use ``deck.identifiers.heading_to_id`` when you need the anchor that
    ``pres shot --slide <id>`` selects on.
    """
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


class DepartmentType(str, Enum):
    ENGE = "ENGE"
    CS = "CS"
    VT = "VT"


class PartialType(str, Enum):
    INTRO = "intro"
    AGENDA = "agenda"
    CREDITS = "credits"
    THANK_YOU = "thank-you"


class SlideType(str, Enum):
    BULLET_LIST = "bullet-list"
    TEXT_WITH_IMAGE = "text-with-image"
    SECTION_DIVIDER = "section-divider"
    THREE_CARDS = "three-cards"
    TEXT_WITH_QUESTION = "text-with-question"


class SlideCount(BaseModel):
    slide_type: SlideType
    count: Annotated[int, Field(ge=1, le=20)]


class PresentationConfig(BaseModel):
    title: str
    subtitle: str | None
    author: str
    date: date
    slug: str
    department: DepartmentType
    partials: list[PartialType]
    slides: list[SlideCount]
    show_section_header: bool = False

    @field_validator("slug")
    @classmethod
    def slug_must_be_safe(cls, v: str) -> str:
        cleaned = safe_slug(v)
        if not cleaned:
            raise ValueError("Slug cannot be empty after sanitization")
        return cleaned

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()
