from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("slug")
    @classmethod
    def slug_must_be_safe(cls, v: str) -> str:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", v.lower().replace(" ", "-")).strip("-")
        if not cleaned:
            raise ValueError("Slug cannot be empty after sanitization")
        return cleaned

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()
