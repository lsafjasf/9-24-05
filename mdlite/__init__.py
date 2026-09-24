"""mdlite: a safe Markdown-subset to HTML renderer (stdlib only).

Pipeline: lexer -> parser -> renderer. The renderer only consumes the
parser's AST. Errors are reported with line/col positions, never raised
as uncaught exceptions.

Public API:
    render(text) -> (html, errors)
    render_stream(lines, out) -> errors
"""
from __future__ import annotations

import io
from typing import Iterable, List, TextIO, Tuple

from .errors import MarkdownError
from .lexer import lex
from .parser import iter_blocks
from .renderer import render_block, sanitize_url

__all__ = ["render", "render_stream", "MarkdownError", "sanitize_url"]
__version__ = "0.1.0"


def render_stream(lines: Iterable[str], out: TextIO) -> List[MarkdownError]:
    """Render a line stream to `out`, block by block.

    Memory stays bounded by the largest single block, not by the size of
    the whole document, so multi-tens-of-MB inputs are fine.
    """
    errors: List[MarkdownError] = []
    for block in iter_blocks(lex(lines), errors):
        render_block(block, out)
    return errors


def render(text: str) -> Tuple[str, List[MarkdownError]]:
    """Render a Markdown string, returning (html, errors)."""
    out = io.StringIO()
    errors = render_stream(text.splitlines(keepends=True), out)
    return out.getvalue(), errors
