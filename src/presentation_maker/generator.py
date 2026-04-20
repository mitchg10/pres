from __future__ import annotations

import shutil
from pathlib import Path

from presentation_maker.models import PresentationConfig
from presentation_maker.templates import render_index_qmd, render_logo_inject_html, render_quarto_yml

# Resolved at import time: src/presentation_maker/ -> src/ -> project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def get_presentations_dir() -> Path:
    return PROJECT_ROOT / "presentations"


def presentation_exists(slug: str) -> bool:
    return (get_presentations_dir() / slug).exists()


def scaffold_presentation(config: PresentationConfig) -> Path:
    target_dir = get_presentations_dir() / config.slug
    if target_dir.exists():
        raise FileExistsError(
            f"Presentation '{config.slug}' already exists at {target_dir}"
        )
    target_dir.mkdir(parents=True, exist_ok=False)
    _write_file(target_dir / "_quarto.yml", render_quarto_yml(config))
    _write_file(target_dir / "index.qmd", render_index_qmd(config))
    _write_file(target_dir / "logo-inject.html", render_logo_inject_html(config))
    _copy_images(target_dir)
    return target_dir


def _copy_images(target_dir: Path) -> None:
    src = PROJECT_ROOT / "images"
    dst = target_dir / "images"
    if src.exists():
        shutil.copytree(src, dst)


def list_presentations() -> list[dict[str, str]]:
    pres_dir = get_presentations_dir()
    if not pres_dir.exists():
        return []
    return [
        {
            "slug": child.name,
            "title": _extract_title(child / "index.qmd"),
            "path": str(child),
        }
        for child in sorted(pres_dir.iterdir())
        if child.is_dir()
    ]


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _extract_title(qmd_path: Path) -> str:
    try:
        for line in qmd_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"')
    except OSError:
        pass
    return qmd_path.parent.name
