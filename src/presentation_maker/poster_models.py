from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from presentation_maker.models import DepartmentType


class ResearchGroupLogo(str, Enum):
    IDEEAS_HORIZONTAL = "ideeas-h"
    IDEEAS_VERTICAL = "ideeas-v"
    IDEEAS_ICON = "ideeas-icon"
    NONE = "none"


class PosterConfig(BaseModel):
    title: str
    subtitle: str | None
    authors: str
    institution: str
    date: date
    slug: str
    department: DepartmentType
    research_group_logo: ResearchGroupLogo
    include_nsf: bool
    nsf_grant_number: str | None
    columns: Annotated[int, Field(ge=1, le=6)]
    rows: Annotated[int, Field(ge=1, le=8)]
    color_scheme: str

    @field_validator("slug")
    @classmethod
    def slug_must_be_safe(cls, v: str) -> str:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", v.lower().replace(" ", "-")).strip("-")
        if not cleaned:
            raise ValueError("Slug cannot be empty after sanitization")
        return cleaned

    @field_validator("title", "authors", "institution")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()
