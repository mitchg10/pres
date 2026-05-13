# presentation-maker

CLI tool that scaffolds Quarto RevealJS presentations for the IDEEAS Lab.

---

## Requirements

Install these before anything else:

- **Python 3.13+** — [python.org/downloads](https://www.python.org/downloads/)
- **uv** — [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)
- **Quarto** — [quarto.org/docs/get-started](https://quarto.org/docs/get-started/) *(only needed for `pres preview`)*

---

## Install

```bash
git clone <repo-url>
cd presentation-maker
uv sync
```

That's it. `uv sync` installs all dependencies automatically.

---

## Commands

Run any command with `uv run pres <command>`.

| Command | What it does |
|---|---|
| `uv run pres new` | Interactive wizard — creates a new presentation |
| `uv run pres list` | Shows all presentations you've created |
| `uv run pres preview <slug>` | Opens a live preview in your browser |
| `uv run pres open <slug>` | Opens the presentation folder in Finder (macOS) |
| `uv run pres pdf <slug>` | Prints the presentation as a PDF |

The `<slug>` is the folder name the wizard gives your presentation (e.g. `my-talk`).

---

## What the Wizard Asks

When you run `uv run pres new`, the wizard walks you through these prompts in order:

| Prompt | Description |
|---|---|
| **Presentation title** | Required. The main title of your talk. |
| **Subtitle** | Optional. Press Enter to skip. |
| **Author name** | Required. Your name as it appears on the title slide. |
| **Date** | Defaults to today in `YYYY-MM-DD` format. Edit or press Enter to accept. |
| **Folder name (slug)** | Auto-generated from the title (e.g. `my-talk`). Edit if you want a different folder name. |
| **Department** | Choose one: Engineering Education (ENGE), Computer Science (CS), or Virginia Tech (VT). Controls the logo and color theme. |
| **Shared partials** | Multi-select (Space to toggle, Enter to confirm). Options: Intro / About Speaker, Agenda, Credits / Lab Team, Thank You / Q&A. |
| **Content slide types** | Multi-select. Options: Bullet List, Text with Image, Section Divider, Three Cards, Text with Question. |
| **Slide count** | For each slide type you selected, how many placeholder slides to generate (1–20). |
| **Floating section header** | Yes/No. Whether to show a navigation header that highlights the current section. Defaults to No. |

---

## Workflow

1. **Create** — run `uv run pres new` and answer the prompts (title, author, slide types, etc.)
2. **Edit** — open `presentations/<slug>/index.qmd` in any text editor and replace the placeholder text with your content
3. **Preview** — run `uv run pres preview <slug>` to see it live in your browser

Your presentations are saved in the `presentations/` folder.

---

## Editing Files

### Presentation content
Edit `presentations/<slug>/index.qmd` — this is your slides file. Each slide starts with `##`. Replace placeholder text with your content.

### Brand colors
Edit `_brand.yml` — the `color.palette` block defines every named color. The `primary` and `secondary` keys control the main accent colors used across all slides.

### Slide styles and components
Edit `styles/components.scss` — controls layout, font sizes, card styles, and other visual elements. Each section is labeled with a comment (e.g. `/* ── Card ── */`).

### Reusable sections (partials)
Edit files in `partials/` — these are shared sections included across presentations:

| File | Section |
|---|---|
| `partials/_intro.qmd` | About the Speaker |
| `partials/_agenda.qmd` | Agenda |
| `partials/_credits.qmd` | Lab Team / Credits |
| `partials/_thank-you.qmd` | Thank You / Q&A with name (CHANGE) | 

### Per-presentation settings
Edit `presentations/<slug>/_quarto.yml` — controls the title, author, theme, logo, and other Quarto settings specific to that presentation.
