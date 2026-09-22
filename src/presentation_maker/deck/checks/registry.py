"""The checks that run by default, in the order their diagnostics read best."""

from __future__ import annotations

from presentation_maker.deck.checks.assets import (
    asset_missing,
    asset_not_web_renderable,
    include_missing,
)
from presentation_maker.deck.checks.base import Check
from presentation_maker.deck.checks.identity import slide_id_drift, slide_id_duplicate

__all__ = ["REGISTRY"]

REGISTRY: tuple[Check, ...] = (
    slide_id_duplicate,
    slide_id_drift,
    asset_missing,
    asset_not_web_renderable,
    include_missing,
)
