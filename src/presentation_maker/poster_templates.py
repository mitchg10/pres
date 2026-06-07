from __future__ import annotations

from textwrap import dedent

from presentation_maker.poster_models import PosterConfig, ResearchGroupLogo

_LOGO_FILENAMES: dict[ResearchGroupLogo, str | None] = {
    ResearchGroupLogo.IDEEAS_HORIZONTAL: "IDEEAS_h_color.png",
    ResearchGroupLogo.IDEEAS_VERTICAL: "IDEEAS_v_color.png",
    ResearchGroupLogo.IDEEAS_ICON: "ideeas_icon_only_color.png",
    ResearchGroupLogo.NONE: None,
}


def render_poster_quarto_yml() -> str:
    return dedent("""\
        project:
          type: default

        format:
          html:
            theme:
              - ../../styles/poster.scss
              - ../../styles/poster_elements.scss
              - styles.scss
            toc: false
            self-contained: true
            page-layout: custom
    """)


def render_poster_index_qmd(config: PosterConfig) -> str:
    header = _render_poster_header(config)
    grid = _render_poster_grid(config)
    return "\n".join([
        "---",
        'title: ""',
        "format: html",
        "---",
        "",
        ":::: {#poster-wrapper}",
        "",
        header,
        "",
        "::: {#poster-body}",
        grid,
        ":::",
        "",
        "::: {#poster-footer}",
        "<!-- Add contact information, QR codes, or acknowledgements here -->",
        ":::",
        "",
        "::::",
        "",
    ])


def render_poster_styles_scss() -> str:
    return "/*-- scss:rules --*/\n/* Add poster-specific overrides here */\n"


def _render_poster_header(config: PosterConfig) -> str:
    logo_col = _render_logo_column(config.research_group_logo)
    title_block = _render_title_block(config)
    dept_col = _render_dept_column(config)
    return "\n".join([
        f"::: {{#poster-header .header-{config.color_scheme}}}",
        ":::: {.columns}",
        '::: {.column width="20%"}',
        logo_col,
        ":::",
        '::: {.column width="60%"}',
        title_block,
        ":::",
        '::: {.column width="20%"}',
        dept_col,
        ":::",
        "::::",
        ":::",
    ])


def _render_logo_column(logo: ResearchGroupLogo) -> str:
    filename = _LOGO_FILENAMES[logo]
    if filename is None:
        return ""
    return f"![](images/{filename})"


def _render_title_block(config: PosterConfig) -> str:
    lines = [f"# {config.title}"]
    if config.subtitle:
        lines.append(f"### {config.subtitle}")
    meta = f"{config.authors} · {config.institution} · {config.date.isoformat()}"
    lines.append(meta)
    return "\n\n".join(lines)


def _render_dept_column(config: PosterConfig) -> str:
    dept = config.department.value
    parts = [f"![](images/{dept}_white.png)"]
    if config.include_nsf:
        parts.append("![](images/NSF.png)")
        if config.nsf_grant_number:
            parts.append(f"Grant {config.nsf_grant_number}")
    return "\n\n".join(parts)


def _render_poster_grid(config: PosterConfig) -> str:
    total = config.columns * config.rows
    cells: list[str] = []
    for i in range(1, total + 1):
        cells.extend([
            "::: {.poster-cell}",
            f"### Panel {i}",
            "",
            "<!-- Add your content here -->",
            ":::",
            "",
        ])
    return "\n".join([
        f":::: {{.poster-grid .cols-{config.columns} .rows-{config.rows}}}",
        *cells,
        "::::",
    ])
