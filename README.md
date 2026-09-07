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
| `uv run pres preview <slug> --network` | Same, but also viewable on your phone (see below) |
| `uv run pres open <slug>` | Opens the presentation folder in Finder (macOS) |
| `uv run pres pdf <slug>` | Prints the presentation as a PDF |
| `uv run pres shot <slug>` | Screenshots the slides to PNG (see below) |
| `uv run pres poster shot <slug>` | Screenshots a poster to PNG |

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

### Previewing on your phone

Add `--network` (or `-n`) to view the live preview on a phone or tablet:

```bash
uv run pres preview <slug> --network
```

The terminal prints a URL like `http://192.168.1.117:4200` along with a QR code — scan it with
your phone's camera to open the slides. Edits still reload live on the phone as you save.

- Your phone must be on the **same WiFi network** as your laptop.
- macOS may ask to allow incoming network connections the first time — click **Allow**.
- While the preview runs, anyone on that WiFi network can view the presentation. Stop it with
  `Ctrl-C` when you're done.
- Port 4200 is used by default; if it's busy the next free port is chosen automatically. Pass
  `--port <number>` to pick your own.

### Screenshotting slides

`pres shot` renders the deck and saves PNGs of the slides, without opening a browser window.
Useful for checking a change quickly, dropping a slide into an email, or letting an AI coding
assistant see its own work.

```bash
uv run pres shot my-talk                     # every slide
uv run pres shot my-talk --slide 4           # one slide, counting from 0
uv run pres shot my-talk --slide the-agenda  # one slide, by its heading
uv run pres shot my-talk --contact-sheet     # plus one grid image of the whole deck
uv run pres poster shot my-poster            # a poster
```

Images land in `build/shots/<slug>/`, alongside a `capture-report.md` noting any content that
overflowed a slide, browser errors, or files that failed to load. The deck is re-rendered
automatically whenever you have edited it since the last build.

Other options worth knowing:

| Option | What it does |
|---|---|
| `--fragments` | One image per reveal step, so you can check the order things appear |
| `--frames 5 --interval 300` | A burst of images over time, for checking animations |
| `--width 1920 --height 1080` | Full resolution (the default 1280×720 is smaller but accurate) |
| `--out <dir>` | Write somewhere other than `build/shots/` |

---

## Working with AI Coding Agents

Slides are HTML rendered in a browser, so an AI assistant editing your `.qmd` file cannot tell
whether the change looked right. `pres shot` closes that loop: the assistant edits, captures the
slide, and looks at the image before telling you it's done.

[`AGENTS.md`](AGENTS.md) in this folder explains that workflow to any assistant. It is plain
Markdown and not tied to a particular tool — Codex, Cursor, and Gemini CLI read it on their own,
and any other assistant can simply be told to read it first.

Two tools get a small pointer file so they pick it up automatically:

- **Cursor** — `.cursor/rules/preview-slides.mdc`
- **GitHub Copilot** — `.github/copilot-instructions.md`

**Claude Code** users can install a skill that triggers on its own after a slide edit:

```bash
cp -R .claude.example/skills .claude/skills
```

See [`.claude.example/README.md`](.claude.example/README.md) for what else is in there. Your own
`.claude/` folder is gitignored, so your settings stay local.

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
