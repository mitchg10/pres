"""Source-level model of a Quarto deck.

Unlike the ``capture_*`` modules, nothing in here renders, launches a browser or
reads ``index.html``: this package answers questions about the ``.qmd`` source.

Two conventions hold throughout, and both exist so the package stays usable from
a test with a ``tmp_path`` fixture or from any working directory:

* Nothing here resolves the project root itself. Every entry point takes an
  explicit root or deck path; ``generator.project_root()`` is a CLI convenience.
* Models are frozen and functions are pure. Parsing a deck twice gives two equal
  values, never two views of shared mutable state.

The package is nested rather than following the flat ``capture_*`` / ``poster_*``
prefix convention because it grows to roughly fifteen modules, which would
otherwise drown the package root.

``bridge`` is deliberately **not** re-exported here. It is the one module that
points back out at the capture layer, so importing it eagerly would make the whole
package depend on ``capture_models`` — and ``capture_models`` imports ``Diagnostic``
from here. Import it as ``from presentation_maker.deck.bridge import to_slide_refs``.
"""

from presentation_maker.deck.identifiers import disambiguate, heading_to_id
from presentation_maker.deck.models import (
    AssetRef,
    DeckModel,
    IncludeRef,
    PandocAttrs,
    Slide,
    SourceLine,
    SourcePos,
)
from presentation_maker.deck.parser import parse_deck

__all__ = [
    "AssetRef",
    "DeckModel",
    "IncludeRef",
    "PandocAttrs",
    "Slide",
    "SourceLine",
    "SourcePos",
    "disambiguate",
    "heading_to_id",
    "parse_deck",
]
