from __future__ import annotations

import shutil
from pathlib import Path

from presentation_maker import generator
from presentation_maker.poster_models import PosterConfig
from presentation_maker.poster_templates import (
    render_poster_index_qmd,
    render_poster_quarto_yml,
    render_poster_styles_scss,
)


def scaffold_poster(config: PosterConfig) -> Path:
    target_dir = generator.get_posters_dir() / config.slug
    if target_dir.exists():
        raise FileExistsError(
            f"Poster '{config.slug}' already exists at {target_dir}"
        )
    target_dir.mkdir(parents=True, exist_ok=False)
    _write_file(target_dir / "_quarto.yml", render_poster_quarto_yml())
    _write_file(target_dir / "index.qmd", render_poster_index_qmd(config))
    _write_file(target_dir / "styles.scss", render_poster_styles_scss())
    _copy_images(target_dir)
    return target_dir


def list_posters() -> list[dict[str, str]]:
    posters_dir = generator.get_posters_dir()
    if not posters_dir.exists():
        return []
    return [
        {
            "slug": child.name,
            "title": _extract_title(child / "index.qmd"),
            "path": str(child),
        }
        for child in sorted(posters_dir.iterdir())
        if (child / "index.qmd").exists()
    ]


def _copy_images(target_dir: Path) -> None:
    src = generator.PROJECT_ROOT / "images"
    dst = target_dir / "images"
    if src.exists():
        shutil.copytree(src, dst)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _extract_title(qmd_path: Path) -> str:
    try:
        for line in qmd_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return qmd_path.parent.name
