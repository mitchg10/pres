from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

STANDALONE_SUFFIX = "-standalone.html"

_PROFILE_NAME = "pres-embed"
_PROFILE_FILENAME = f"_quarto-{_PROFILE_NAME}.yml"

# `chalkboard` ships as a reveal plugin marked `self-contained: false`, so Quarto
# refuses to render at all while it is on. A `-M chalkboard:false` override does
# not help: the deck's own `format.revealjs` block wins over top-level metadata.
# A render profile is the one mechanism that merges *into* that format block.
_PROFILE_CONTENT = """\
format:
  revealjs:
    embed-resources: true
    chalkboard: false
"""


def standalone_output_path(slug: str, pres_dir: Path, output: Path | None = None) -> Path:
    """Where a standalone export lands: <slug>-standalone.html unless overridden."""
    if output is None:
        return pres_dir / f"{slug}{STANDALONE_SUFFIX}"
    return output.expanduser().resolve()


def _build_render_command(qmd: Path, output_name: str) -> list[str]:
    """Pure argv builder, kept separate so it is testable without running Quarto."""
    return [
        "quarto",
        "render",
        qmd.name,
        "--profile",
        _PROFILE_NAME,
        "--output",
        output_name,
    ]


def export_standalone_html(
    slug: str,
    pres_dir: Path,
    *,
    output: Path | None = None,
    quiet: bool = False,
) -> Path:
    """Render a deck to a single HTML file with every resource embedded.

    Unlike `pdf.ensure_html_rendered` this always renders, never reuses a stale
    build, and never writes `index.html` — the normal build and its `index_files/`
    directory are left exactly as they were.

    The render runs from `pres_dir`, *not* the project root. Pandoc resolves the
    `index_files/...` resource URLs it is inlining relative to the working
    directory, so running from the project root silently produces a file that is
    missing reveal.js itself.
    """
    qmd = pres_dir / "index.qmd"
    if not qmd.exists():
        raise FileNotFoundError(f"index.qmd not found in {pres_dir}")

    destination = standalone_output_path(slug, pres_dir, output)
    rendered_name = f"{slug}{STANDALONE_SUFFIX}"
    rendered = pres_dir / rendered_name
    profile = pres_dir / _PROFILE_FILENAME
    if profile.exists():
        raise FileExistsError(
            f"{profile} already exists — it is written and removed by 'pres export'. "
            "Move it aside and retry."
        )

    try:
        profile.write_text(_PROFILE_CONTENT, encoding="utf-8")
        subprocess.run(
            _build_render_command(qmd, rendered_name),
            cwd=str(pres_dir),
            check=True,
            stdout=subprocess.DEVNULL if quiet else None,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"'quarto render' failed for '{slug}'. Embedding downloads the CDN "
            "assets the deck links to, so this also fails without network access."
        ) from error
    finally:
        profile.unlink(missing_ok=True)

    if not rendered.exists():
        raise RuntimeError(f"Quarto reported success but {rendered} was not written.")

    # Embedding should leave no supporting directory; clean one up rather than
    # ship a single file that looks like it still has a dependency beside it.
    supporting = pres_dir / f"{slug}{STANDALONE_SUFFIX.removesuffix('.html')}_files"
    if supporting.is_dir():
        shutil.rmtree(supporting)

    if destination != rendered:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(rendered), str(destination))
    return destination
