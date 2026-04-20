from __future__ import annotations

from datetime import date

import questionary
from rich.console import Console
from rich.panel import Panel

from presentation_maker import generator
from presentation_maker.models import (
    DepartmentType,
    PartialType,
    PresentationConfig,
    SlideCount,
    SlideType,
)
from presentation_maker.templates import slug_from_title

console = Console()


def run_wizard() -> PresentationConfig:
    console.print(Panel("[bold blue]Presentation Wizard[/bold blue]", expand=False))
    title = _prompt_title()
    subtitle = _prompt_subtitle()
    author = _prompt_author()
    presentation_date = _prompt_date()
    slug = _prompt_slug(title)
    department = _prompt_department()
    partials = _prompt_partials()
    slides = _prompt_slides()
    return PresentationConfig(
        title=title,
        subtitle=subtitle,
        author=author,
        date=presentation_date,
        slug=slug,
        department=department,
        partials=partials,
        slides=slides,
    )


def _prompt_title() -> str:
    return questionary.text(
        "Presentation title:",
        validate=lambda t: bool(t.strip()) or "Title cannot be blank",
    ).ask()


def _prompt_subtitle() -> str | None:
    value = questionary.text("Subtitle (optional, press Enter to skip):").ask()
    return value.strip() or None


def _prompt_author() -> str:
    return questionary.text(
        "Author name:",
        validate=lambda t: bool(t.strip()) or "Author cannot be blank",
    ).ask()


def _prompt_date() -> date:
    def _validate_date(v: str) -> bool | str:
        try:
            date.fromisoformat(v)
            return True
        except ValueError:
            return "Enter a date in YYYY-MM-DD format"

    raw = questionary.text(
        "Date (YYYY-MM-DD):",
        default=date.today().isoformat(),
        validate=_validate_date,
    ).ask()
    return date.fromisoformat(raw)


def _prompt_slug(title: str) -> str:
    default = slug_from_title(title)
    while True:
        slug = questionary.text("Folder name (slug):", default=default).ask()
        if not generator.presentation_exists(slug):
            return slug
        console.print(
            f"[yellow]A presentation named '{slug}' already exists. Choose another.[/yellow]"
        )
        default = f"{slug}-2"


def _prompt_department() -> DepartmentType:
    return questionary.select(
        "Department:",
        choices=[
            questionary.Choice("Engineering Education (ENGE)", value=DepartmentType.ENGE),
            questionary.Choice("Computer Science (CS)", value=DepartmentType.CS),
            questionary.Choice("Virginia Tech (VT)", value=DepartmentType.VT),
        ],
    ).ask()


def _prompt_partials() -> list[PartialType]:
    choices = [
        questionary.Choice("Intro / About Speaker", value=PartialType.INTRO),
        questionary.Choice("Agenda", value=PartialType.AGENDA),
        questionary.Choice("Credits / Lab Team", value=PartialType.CREDITS),
        questionary.Choice("Thank You / Q&A", value=PartialType.THANK_YOU),
    ]
    selected: list[PartialType] = questionary.checkbox(
        "Include shared partials (space to select, enter to confirm):",
        choices=choices,
    ).ask()
    return selected or []


def _prompt_slides() -> list[SlideCount]:
    choices = [
        questionary.Choice("Bullet List", value=SlideType.BULLET_LIST),
        questionary.Choice("Text with Image", value=SlideType.TEXT_WITH_IMAGE),
        questionary.Choice("Section Divider", value=SlideType.SECTION_DIVIDER),
        questionary.Choice("Three Cards", value=SlideType.THREE_CARDS),
        questionary.Choice("Text with Question", value=SlideType.TEXT_WITH_QUESTION),
    ]
    selected_types: list[SlideType] = questionary.checkbox(
        "Which content slide types to include:",
        choices=choices,
    ).ask()
    if not selected_types:
        return []
    return [_prompt_slide_count(slide_type) for slide_type in selected_types]


def _prompt_slide_count(slide_type: SlideType) -> SlideCount:
    label = slide_type.value.replace("-", " ").title()
    raw = questionary.text(
        f"How many {label} slides?",
        default="1",
        validate=lambda v: (v.isdigit() and 1 <= int(v) <= 20) or "Enter a number between 1 and 20",
    ).ask()
    return SlideCount(slide_type=slide_type, count=int(raw))
