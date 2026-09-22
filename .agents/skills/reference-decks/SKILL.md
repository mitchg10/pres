---
name: reference-decks
description: Find and view existing presentations in this repo for design guidance — layouts, cards, columns, fragments, GSAP animations, title slides, section dividers, custom SCSS. Use when building or restyling any deck, when the user says "make it like the fulbright deck" or "match the house style", when choosing how to lay out a slide, and before inventing a new component or animation from scratch — another deck here has almost certainly solved it already.
---

# Reference decks

This repo is its own pattern library: 10+ finished decks and a poster, all sharing the
same brand theme. Before designing a slide from scratch, find who already did it well
and borrow from them. This skill is about finding and *viewing* those decks; once you
edit, switch to `preview-slides` to verify your own work.

## Step 1 — Index the decks

```bash
uv run python .agents/skills/reference-decks/scripts/deck-index.py
```

One line per deck: slide/fragment/column counts, whether it uses GSAP, partials count,
deck-local SCSS size, and how many classes it defines locally. Run from anywhere; the
script locates the repo relative to itself.

Find decks that demonstrate a specific pattern:

```bash
uv run python .agents/skills/reference-decks/scripts/deck-index.py --pattern "discussion-box"
uv run python .agents/skills/reference-decks/scripts/deck-index.py --pattern "gsap|auto-animate"
```

`--pattern` is a regex over every source file (index.qmd, partials, styles.scss,
_quarto.yml) and prints which files matched. It covers partials, which matter — some
decks keep entire sections, including their animations, in `partials/` rather than
`index.qmd`.

For one deck's detail view (slide headings with their `--slide` ids, the partials it
actually includes, deck-local class names):

```bash
uv run python .agents/skills/reference-decks/scripts/deck-index.py --deck <slug>
```

Slide ids and ordering come from `presentation_maker.deck`, the parser `pres check`
uses, so they match what pandoc builds and can be pasted straight into `--slide`. For
the same list as JSON, plus any problems in the deck, `uv run pres check <slug> --json`
says more.

## Step 2 — See it rendered

Source tells you *what* a deck does; only a capture tells you whether it looks good.

```bash
uv run pres shot <slug> --contact-sheet   # skim the whole deck as one tiled grid
uv run pres shot <slug> --slide <id>      # one slide, all fragments revealed
```

Read the PNG the command prints (output in `build/shots/<slug>/`). Use the heading ids
from `--deck <slug>` — they survive slide reordering, indices do not. Indices are
zero-based.

## Step 3 — Borrow correctly

The trap when copying markup between decks: some classes come free, some don't.

- **Shared classes** (defined in root `styles/components.scss`) work in every deck
  automatically — `.card--maroon`, `.card--burnt-orange` and friends, `.discussion-box`,
  `.gotcha-box`, `.headshot`, `.citation`, `.credits-col`, `.chaos-*`. Copy the markup,
  nothing else.
- **Deck-local classes** only exist where the deck's own `styles.scss` defines them. The
  `--deck <slug>` view lists them by name. If you copy markup that uses them, copy the
  matching rules from that deck's `styles.scss` into yours too.
- **Colors** come from `_brand.yml` via SCSS variables (`$brand-color-maroon`, …). Prefer
  those over hex literals.
- **GSAP animations** are plain `<script>` in the qmd or a partial — see
  `cs-6204-dex/_dex-flow-animation.qmd` for a full worked example. GSAP loads from a CDN,
  so offline captures show it missing; check `capture-report.md` before "fixing" a
  frozen animation.
- **Section dividers** set their own background via heading attributes
  (`## Title {background-color="#642667"}`). A card that reads fine on white can
  disappear on one of these — verify contrast in the capture.

## Scouting tips

- Rich deck-local styling (73 and 68 custom classes): `asr-transcription`,
  `wfd-skill-extraction`, `responsible-genai-use`.
- Most fragments, longest deck: `wfd-skill-extraction` (45 fragments, 40 slides).
- GSAP-heavy section partials: `fulbright-ai-capabilities/partials/`.
- Columns layouts: `cs-6204-dex` (19 uses), `wfd-skill-extraction`.
- Posters are separate (`posters/`, captured with `pres poster shot`); the index covers
  them too (kind `p`).

These tips go stale as decks are added — trust the index script over this list.