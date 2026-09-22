# Working on this repo as a coding agent

This project scaffolds Quarto RevealJS presentations and 24×36in academic posters.
Slides are HTML rendered in a browser, so **you cannot tell whether an edit worked by
reading the source**. Render it and look at it.

This file is tool-agnostic. Any agent — Claude Code, Codex, Cursor, Gemini CLI, Aider,
Copilot — should read it before editing slides.

---

## The loop

1. **Edit** the source (`presentations/<slug>/index.qmd`, a partial, or the shared styling).
2. **Check it** — sub-second, no render, no browser:
   ```bash
   uv run pres check <slug>
   ```
   This catches the problems that survive a successful build: duplicate slide ids,
   image paths that point at nothing, includes that resolve nowhere. Fix these first;
   a capture of a deck with a duplicate id may not even be the slide you asked for.
3. **Capture** it:
   ```bash
   uv run pres shot <slug> --slide <n>
   ```
4. **Open the PNG it wrote** and actually look at it. This step is the entire point — a
   capture you never view tells you nothing. The command prints the output paths.
5. **Read `capture-report.md`** in the same directory. It lists content that overflowed a
   slide, console errors, failed requests, and the source problems from step 2 — all
   things that are easy to miss in an image.
6. Iterate until it looks right.

Output lands in `build/shots/<slug>/` (gitignored) unless you pass `--out`.

---

## Commands

| Command | What it does |
|---|---|
| `uv run pres list` | Slugs of every presentation |
| `uv run pres check` | Static checks over every deck's source |
| `uv run pres check <slug>` | Check one deck |
| `uv run pres check <slug> --json` | Slide list plus diagnostics, machine-readable |
| `uv run pres shot <slug>` | Capture every slide |
| `uv run pres shot <slug> --slide 4` | One slide, by zero-based index |
| `uv run pres shot <slug> --slide the-failure-categories` | One slide, by id |
| `uv run pres shot <slug> --slide 2-5` | An inclusive range |
| `uv run pres shot <slug> --slide 0,4,agenda` | A comma-separated mix |
| `uv run pres shot <slug> -s 4 --fragments` | One image per fragment reveal step |
| `uv run pres shot <slug> -s 4 --frames 5 --interval 300` | Timed frames, for animations |
| `uv run pres shot <slug> --contact-sheet` | Plus one tiled grid of the whole deck |
| `uv run pres poster shot <slug>` | Capture a poster as a single PNG |
| `uv run pres preview <slug>` | Live browser preview (long-running; for a human) |
| `uv run pres pdf <slug>` | Export the deck to PDF |
| `uv run pres export <slug>` | Bundle the deck into one self-contained HTML file |

Useful flags: `--width 1920 --height 1080` when you need to inspect fine detail (the default
1280×720 is a faithful but cheaper image, since reveal scales the deck); `--out DIR` to keep a
capture separate; `--no-render` to skip the rebuild; `--json` for machine-readable output;
`--url` to shoot an already-running `pres preview` instead of re-rendering.

`--fragments` and `--frames` capture different things — use one at a time.

### Which mode to use

| You changed | Capture with |
|---|---|
| Text or layout on one slide | `--slide <id>` |
| `styles/components.scss`, `_brand.yml` — anything shared | `--contact-sheet` (scan the whole deck) |
| Fragment ordering or `.fragment` classes | `--fragments` |
| A GSAP or CSS animation | `--frames 5 --interval 300` |
| A poster | `pres poster shot <slug>` |

---

## What to look for in a capture

- **Overflow** — content running off the bottom or right of the slide. The report flags this
  numerically; trust it over your reading of the image.
- **Contrast** — light text on a light card, or dark on dark. Section dividers set their own
  `background-color`, so a card that reads fine elsewhere can disappear on one.
- **The logo and footer** — injected at runtime by `logo-inject.html`. If they are missing,
  something broke in the deck's JavaScript; check the report's console errors.
- **Fragment order** — with `--fragments`, each step should reveal exactly one thing.
- **Column balance** — `:::: {.columns}` blocks with lopsided or overlapping halves.

---

## How the decks are built

- **Slides are `##` headings** in `presentations/<slug>/index.qmd`. Each becomes one slide.
- **Slide ids** are slugs of those headings (`## The Failure Categories` →
  `the-failure-categories`). Prefer ids over indices in `--slide`: they survive slide reordering.
- **`pres check` reads the source, `pres shot` reads the render.** They catch disjoint
  problems and neither replaces the other: a broken image path builds cleanly and only
  `check` sees it; a card whose text overflows parses cleanly and only `shot` sees it.
- **Slide indices are zero-based** — the title slide is `0`. This matches the `#/N` URL hash,
  because the decks are generated with `hashOneBasedIndex: false`. Note the on-screen slide
  counter is one-based, so slide `5` displays as "6 / 9".
- **Fragments** are `::: {.fragment .fade-up}` blocks. Fragments sharing a `fragment-index`
  reveal together and count as one step.
- **Cards and components** live in `styles/components.scss` (`.card--maroon`, `.discussion-box`,
  `.gotcha-box`, and friends). Colors come from `_brand.yml`.
- **Shared sections** are in `partials/` and pulled in with `{{< include partials/_agenda.qmd >}}`.
- **Posters** are `format: html`, `self-contained: true`, laid out with `.poster-grid` /
  `.poster-cell`, themed by `styles/poster.scss` and `styles/poster_elements.scss`.

---

## Consulting other decks

The finished decks are the house pattern library. Before designing a layout, card, or
animation from scratch, check whether another deck already solved it:

```bash
uv run python .agents/skills/reference-decks/scripts/deck-index.py                 # index all decks
uv run python .agents/skills/reference-decks/scripts/deck-index.py --pattern gsap  # who does X
uv run python .agents/skills/reference-decks/scripts/deck-index.py --deck <slug>   # slide ids, classes
```

Then capture the reference deck (`pres shot <slug> --contact-sheet`) and read the image.
When borrowing markup, remember: classes from the shared `styles/components.scss` work
everywhere; classes defined in a deck's own `styles.scss` must be copied along with the
markup. The full workflow lives in `.agents/skills/reference-decks/SKILL.md`.

---

## Gotchas

- **Decks load GSAP and Font Awesome from CDNs.** Offline, icons and animations are missing from
  the screenshot but fine in the real deck. `capture-report.md` lists the failed requests — check
  there before "fixing" a missing icon.
- **`pres shot` re-renders automatically** when `index.html` is older than any source it is built
  from, including the shared `styles/` and `partials/`. You do not need to run `quarto render`
  yourself, and you should not pass `--no-render` after an edit.
- **Renders run from the project root** so relative image paths resolve. Do not run
  `quarto render` from inside a presentation directory. The one exception is `pres export`, which
  must run from the deck directory — pandoc resolves the `index_files/...` resources it is
  inlining relative to the working directory, and from the project root it silently produces a
  file with reveal.js missing.
- **`index_files/` must sit beside `index.html`** — the normal build is not self-contained. Do not
  move or delete it. When you need a single shareable file, use `pres export` rather than moving
  anything; it writes a separate `<slug>-standalone.html` and leaves the normal build alone.
- **`pres export` turns chalkboard off.** Quarto ships chalkboard as a plugin marked
  `self-contained: false` and refuses to render at all while it is on, so the export writes a
  temporary `_quarto-pres-embed.yml` profile that disables it. A `-M chalkboard:false` override
  does *not* work — the deck's own `format.revealjs` block wins over top-level metadata.
- **`pres preview` never exits.** It is a live server for a person. Use `pres shot` instead; if a
  preview is already running, `--url http://localhost:4200/...` will capture from it.
- **A plain `--slide` capture shows the slide with every fragment revealed**, so you see all of
  its content at once. Use `--fragments` to see the intermediate states.
- **Two headings with the same text silently collide.** Pandoc appends `-1` to the second
  one's id, so `--slide <id>` captures the *first* — often a section divider rather than
  the content slide you meant. `pres check` reports this as `slide-id-duplicate`.
- **`pres check` exits 1 for problems found and 2 for "could not run"**, matching ruff and
  eslint rather than the rest of this CLI, where 1 means failure. That is deliberate: a
  script has to be able to tell a bad deck from a broken checker.

---

## Testing

```bash
uv run pytest -m "not slow"   # fast unit tests
uv run pytest                 # includes browser-backed integration tests
```

The parser behind `pres check` is held to one standard above all: for every deck on the
machine, the slide ids it reads from source must equal the `<section id=...>` list in
that deck's rendered `index.html`, exactly. `tests/test_deck_golden.py` asserts it and
skips when `presentations/` is absent, since that directory is gitignored. If you change
`deck/identifiers.py` or `deck/parser.py`, run the suite somewhere the decks exist.
