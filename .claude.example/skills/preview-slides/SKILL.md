---
name: preview-slides
description: Render and screenshot Quarto RevealJS slides or posters in this repo so you can see how they actually look. Use after editing index.qmd, a partial, styles/components.scss, _brand.yml, a fragment, or an animation — and whenever asked to see, check, show, or look at how a slide, deck, or poster renders.
---

# Preview slides

Slides are HTML rendered in a browser. Reading the `.qmd` source does not tell you whether a
change worked — capture the slide and look at the image.

## The loop

```bash
uv run pres shot <slug> --slide <index-or-id>
```

Then **read the PNG it wrote** (the command prints the paths), and read `capture-report.md`
in the same directory for overflow, console errors, and failed requests.

Output goes to `build/shots/<slug>/`. Iterate until it looks right.

## Picking a mode

| You changed | Capture with |
|---|---|
| One slide's text or layout | `--slide <id>` |
| Shared styling (`styles/components.scss`, `_brand.yml`) | `--contact-sheet` |
| Fragment ordering | `-s <id> --fragments` |
| An animation | `-s <id> --frames 5 --interval 300` |
| A poster | `uv run pres poster shot <slug>` |

Slide ids are slugs of the `##` headings and are more stable than indices. Indices are
zero-based; the on-screen counter is one-based, so slide `5` displays as "6 / 9".

## Full reference

`AGENTS.md` at the repo root — every flag, what to look for in a capture, how the decks are
built, and the gotchas (CDN-loaded icons, automatic re-rendering, `index_files/`). Read it
before doing substantial work on a deck.
