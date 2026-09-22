"""Turn a slide heading into the id pandoc will give it.

Quarto renders each ``##`` heading as a ``<section>`` whose ``id`` is the anchor
``pres shot --slide <id>`` selects on, so this rule has to match pandoc exactly
rather than approximately. It implements pandoc's ``auto_identifiers`` extension
(*not* ``gfm_auto_identifiers``, which strips periods and doubles hyphens).

Do not reach for this when you need a directory or file name -- see the note on
``heading_to_id`` for why those are a different problem with a different answer.

Deliberately stdlib-only, so the ``deck-index.py`` skill script can import it.
"""

from __future__ import annotations

from typing import Iterable

__all__ = ["disambiguate", "heading_to_id", "split_trailing_attrs", "tokenize_attributes"]

# Pandoc keeps these punctuation marks; everything else that is not a letter,
# digit or whitespace is deleted outright.
_KEPT_PUNCTUATION = frozenset("-_.")

_FALLBACK_ID = "section"

_QUOTES = frozenset("\"'")


def heading_to_id(heading: str) -> str:
    """Return the id pandoc assigns to ``heading``.

    ``heading`` is the raw text following ``##``, attribute block included::

        >>> heading_to_id('Paper vs. CloudLab: Hardware {.smaller}')
        'paper-vs.-cloudlab-hardware'
        >>> heading_to_id("What I Couldn't Reproduce")
        'what-i-couldnt-reproduce'
        >>> heading_to_id('The Results {#results-2024}')
        'results-2024'

    The rule, in pandoc's order:

    1. An explicit ``{#id}`` wins verbatim and is never slugified.
    2. Lowercase.
    3. Keep whitespace, alphanumerics and ``-_.``; *delete* everything else.
       This is the step every naive implementation gets wrong by substituting a
       hyphen, which turns ``Couldn't`` into ``couldn-t`` instead of ``couldnt``.
    4. Collapse whitespace runs to single hyphens.
    5. Drop everything before the first *letter*, so ``1975: A Crisis`` becomes
       ``a-crisis``.
    6. Fall back to ``section`` if nothing survives.

    Alphanumeric tests use ``str.isalnum``/``str.isalpha`` rather than an ASCII
    character class, because pandoc keeps non-ASCII letters: ``Why Δ Is Local``
    is ``why-δ-is-local``, and an ASCII rule silently deletes the delta.

    This is *not* a general-purpose slugifier. Ids may contain ``.`` and
    non-ASCII letters, both of which are poor in a filename and worse in a URL
    path segment. For a directory or file name use ``models.slug_must_be_safe``
    or ``capture_naming.sanitize_id`` instead.
    """
    text, attributes = split_trailing_attrs(heading)

    explicit = _explicit_id(attributes)
    if explicit is not None:
        return explicit

    return _slugify(text)


def disambiguate(ids: Iterable[str]) -> tuple[str, ...]:
    """Resolve duplicate ids the way pandoc does, in document order.

        >>> disambiguate(("intro", "body", "intro", "intro"))
        ('intro', 'body', 'intro-1', 'intro-2')

    The first occurrence keeps the bare id and later ones gain ``-1``, ``-2``,
    and so on, skipping any suffix already taken.

    Kept separate from :func:`heading_to_id` because a single heading's id is
    context-free while disambiguation is a property of the whole document -- and
    because a duplicate-id check needs to see the collision before it is papered
    over.
    """
    seen: set[str] = set()
    resolved: list[str] = []

    for candidate in ids:
        unique = candidate
        suffix = 0
        while unique in seen:
            suffix += 1
            unique = f"{candidate}-{suffix}"
        seen.add(unique)
        resolved.append(unique)

    return tuple(resolved)


def _slugify(text: str) -> str:
    """Apply steps 2-6 of the pandoc rule to attribute-free heading text."""
    kept = "".join(
        char
        for char in text.lower()
        if char.isspace() or char.isalnum() or char in _KEPT_PUNCTUATION
    )
    joined = "-".join(kept.split())

    for position, char in enumerate(joined):
        if char.isalpha():
            return joined[position:]

    return _FALLBACK_ID


def split_trailing_attrs(heading: str) -> tuple[str, str]:
    """Split ``Title {.a key="v"}`` into ``("Title", '.a key="v"')``.

    Scans right-to-left so a brace inside a quoted attribute value cannot be
    mistaken for the start of the block. Returns an empty attribute string when
    the heading has no trailing block.
    """
    text = heading.strip()
    if not text.endswith("}"):
        return text, ""

    depth = 0
    quote: str | None = None

    for position in range(len(text) - 1, -1, -1):
        char = text[position]

        if quote is not None:
            if char == quote:
                quote = None
            continue

        if char in _QUOTES:
            quote = char
        elif char == "}":
            depth += 1
        elif char == "{":
            depth -= 1
            if depth == 0:
                return text[:position].strip(), text[position + 1 : -1]

    return text, ""


def _explicit_id(attributes: str) -> str | None:
    """Return the ``#id`` declared in an attribute block, if there is one.

    Tokenises quote-aware so ``background-color="#861F41"`` is read as a
    key/value pair rather than as an id of ``861F41``.
    """
    for token in tokenize_attributes(attributes):
        if token.startswith("#") and len(token) > 1:
            return token[1:]
    return None


def tokenize_attributes(attributes: str) -> tuple[str, ...]:
    """Split an attribute block on whitespace that falls outside quotes.

    A backslash inside a quoted value escapes the next character, so ``\'`` does not
    close the string. Values come back still quoted and still escaped; unquoting is
    `attrs.parse_attrs`'s job, since this function is also used on blocks where the
    quotes matter.
    """
    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False

    for char in attributes:
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in _QUOTES:
            quote = char
            current.append(char)
        elif char.isspace():
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    return tuple(tokens)
