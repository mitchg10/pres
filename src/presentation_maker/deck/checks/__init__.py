"""Static checks over a parsed deck.

Every rule here answers a question about the *source*. Nothing renders, launches a
browser, or measures a layout — `pres shot` owns that contract and owns it well.
"""

from presentation_maker.deck.checks.base import (
    Check,
    CheckContext,
    Diagnostic,
    Severity,
    check,
)
from presentation_maker.deck.checks.registry import REGISTRY
from presentation_maker.deck.checks.runner import INTERNAL_ERROR_RULE, run_checks

__all__ = [
    "INTERNAL_ERROR_RULE",
    "REGISTRY",
    "Check",
    "CheckContext",
    "Diagnostic",
    "Severity",
    "check",
    "run_checks",
]
