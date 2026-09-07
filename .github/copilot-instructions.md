# Copilot instructions

This repo scaffolds Quarto RevealJS presentations and academic posters. Slides are HTML
rendered in a browser, so reading the `.qmd` source does not tell you whether an edit worked.

After changing a deck, capture it and look at the result:

```bash
uv run pres shot <slug> --slide <index-or-id>
```

Then open the PNG it wrote, and read `capture-report.md` beside it for overflow, console
errors, and failed requests.

Full guidance — every flag, capture modes for fragments and animations, what to look for, and
the gotchas — is in [`AGENTS.md`](../AGENTS.md) at the repo root. Read it before doing
substantial work on a presentation.
