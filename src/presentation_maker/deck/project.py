"""Locating a Quarto project and resolving the paths written inside it."""

from __future__ import annotations

import os.path
from pathlib import Path
from urllib.parse import unquote

__all__ = ["find_quarto_project", "resolve_asset"]

_QUARTO_CONFIGS = ("_quarto.yml", "_quarto.yaml")
_EXTERNAL_PREFIXES = ("http://", "https://", "data:", "mailto:", "//")


def find_quarto_project(start: Path) -> Path | None:
    """Nearest directory at or above `start` holding a `_quarto.yml`.

    Each deck directory in this repo has its own config, so the answer is almost
    always the deck directory itself — which is what makes a leading `/` in an asset
    path mean "the deck", not "the repo".
    """
    current = start if start.is_dir() else start.parent
    for candidate in (current.absolute(), *current.absolute().parents):
        if any((candidate / name).exists() for name in _QUARTO_CONFIGS):
            return candidate
    return None


def resolve_asset(raw: str, *, document_dir: Path, project_dir: Path) -> Path | None:
    """Turn a written path into a filesystem path, or None if it does not name one.

    Returns None for URLs, data URIs, and empty targets. Returns a path for anything
    local **whether or not it exists** — existence is a separate question, asked by
    the `asset-missing` check, which wants the resolved path to put in its message.

    `document_dir` is the directory of the *including* document, not of the partial a
    line was written in. Quarto splices partials textually, so a relative path inside
    `partials/_thank-you.qmd` is resolved from the deck root. This is why those
    partials correctly say `../../images/...`.
    """
    target = _strip_query_and_fragment(unquote(raw.strip()))
    if not target or target.lower().startswith(_EXTERNAL_PREFIXES):
        return None
    base = project_dir if target.startswith("/") else document_dir
    return _normalize(base / target.lstrip("/"))


def _normalize(path: Path) -> Path:
    """Collapse `.` and `..` lexically.

    Deliberately not `Path.resolve()`: that follows symlinks, and a diagnostic should
    quote the path the author would recognize. Lexical collapsing also matches how a
    browser resolves the URL, which is what actually loads the asset.
    """
    return Path(os.path.normpath(path))


def _strip_query_and_fragment(target: str) -> str:
    for separator in ("#", "?"):
        target = target.split(separator, 1)[0]
    return target
