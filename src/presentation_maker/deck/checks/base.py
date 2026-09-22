"""The vocabulary every check speaks."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from presentation_maker.deck.models import DeckModel

__all__ = ["Check", "CheckContext", "Diagnostic", "Severity", "check"]


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


class Diagnostic(BaseModel):
    """One problem, addressed to whoever has to fix it.

    `slide_id` and `slide_index` are what make this actionable rather than merely
    informative: they turn a report into the next command to run, which is
    `pres shot <deck> --slide <slide_id>`.
    """

    model_config = ConfigDict(frozen=True)

    rule: str
    severity: Severity
    message: str
    file: Path
    line: int
    end_line: int | None = None
    column: int = 1
    hint: str = ""
    slide_id: str = ""
    slide_index: int | None = None

    def at_least(self, minimum: Severity) -> bool:
        return _RANK[self.severity] <= _RANK[minimum]

    def compact(self) -> str:
        """`file:line:col: severity rule message` — the problem-matcher shape."""
        return (
            f"{self.file}:{self.line}:{self.column}: "
            f"{self.severity.value} {self.rule} {self.message}"
        )


class CheckContext(BaseModel):
    """Everything a check is allowed to look at."""

    model_config = ConfigDict(frozen=True)

    deck: DeckModel
    build_dir: Path | None = None
    """Where `index.html` lives, or None when checks must work from source alone."""

    @property
    def built_html(self) -> Path | None:
        if self.build_dir is None:
            return None
        candidate = self.build_dir / "index.html"
        return candidate if candidate.is_file() else None


class Check(Protocol):
    rule: str
    severity: Severity

    def __call__(self, context: CheckContext) -> Iterable[Diagnostic]: ...


def check(rule: str, severity: Severity):
    """Tag a plain function as a check, so the registry stays a list of functions."""

    def decorate(function):
        function.rule = rule
        function.severity = severity
        return function

    return decorate
