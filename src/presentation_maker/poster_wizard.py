from __future__ import annotations

from datetime import date

import questionary
from rich.console import Console
from rich.panel import Panel

from presentation_maker import generator
from presentation_maker.models import DepartmentType
from presentation_maker.poster_models import PosterConfig, ResearchGroupLogo
from presentation_maker.templates import slug_from_title

console = Console()


def run_poster_wizard() -> PosterConfig:
    console.print(Panel("[bold blue]Poster Wizard[/bold blue]", expand=False))
    title = _prompt_title()
    subtitle = _prompt_subtitle()
    authors = _prompt_authors()
    institution = _prompt_institution()
    poster_date = _prompt_date()
    slug = _prompt_slug(title)
    department = _prompt_department()
    research_group_logo = _prompt_research_group_logo()
    include_nsf = _prompt_include_nsf()
    nsf_grant_number = _prompt_nsf_grant_number() if include_nsf else None
    columns = _prompt_columns()
    rows = _prompt_rows()
    color_scheme = _prompt_color_scheme()
    return PosterConfig(
        title=title,
        subtitle=subtitle,
        authors=authors,
        institution=institution,
        date=poster_date,
        slug=slug,
        department=department,
        research_group_logo=research_group_logo,
        include_nsf=include_nsf,
        nsf_grant_number=nsf_grant_number,
        columns=columns,
        rows=rows,
        color_scheme=color_scheme,
    )


def _prompt_title() -> str:
    return questionary.text(
        "Poster title:",
        validate=lambda t: bool(t.strip()) or "Title cannot be blank",
    ).ask()


def _prompt_subtitle() -> str | None:
    value = questionary.text("Subtitle (optional, press Enter to skip):").ask()
    return value.strip() or None


def _prompt_authors() -> str:
    return questionary.text(
        "Authors (comma-separated):",
        validate=lambda t: bool(t.strip()) or "Authors cannot be blank",
    ).ask()


def _prompt_institution() -> str:
    return questionary.text(
        "Institution:",
        default="Virginia Tech",
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
        if not generator.poster_exists(slug):
            return slug
        console.print(
            f"[yellow]A poster named '{slug}' already exists. Choose another.[/yellow]"
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


def _prompt_research_group_logo() -> ResearchGroupLogo:
    return questionary.select(
        "Research group logo:",
        choices=[
            questionary.Choice("IDEEAS Horizontal", value=ResearchGroupLogo.IDEEAS_HORIZONTAL),
            questionary.Choice("IDEEAS Vertical", value=ResearchGroupLogo.IDEEAS_VERTICAL),
            questionary.Choice("IDEEAS Icon Only", value=ResearchGroupLogo.IDEEAS_ICON),
            questionary.Choice("None", value=ResearchGroupLogo.NONE),
        ],
    ).ask()


def _prompt_include_nsf() -> bool:
    return questionary.confirm(
        "Include NSF logo and grant number?",
        default=False,
    ).ask()


def _prompt_nsf_grant_number() -> str:
    return questionary.text(
        "NSF grant number:",
        validate=lambda t: bool(t.strip()) or "Grant number cannot be blank",
    ).ask()


def _prompt_columns() -> int:
    raw = questionary.text(
        "Number of columns (1–6):",
        default="3",
        validate=lambda v: (v.isdigit() and 1 <= int(v) <= 6) or "Enter a number between 1 and 6",
    ).ask()
    return int(raw)


def _prompt_rows() -> int:
    raw = questionary.text(
        "Number of rows (1–8):",
        default="2",
        validate=lambda v: (v.isdigit() and 1 <= int(v) <= 8) or "Enter a number between 1 and 8",
    ).ask()
    return int(raw)


def _prompt_color_scheme() -> str:
    return questionary.select(
        "Header color:",
        choices=[
            questionary.Choice("Maroon", value="maroon"),
            questionary.Choice("Burnt Orange", value="burnt-orange"),
            questionary.Choice("Hokie Stone", value="hokie-stone"),
            questionary.Choice("White", value="white"),
        ],
    ).ask()
