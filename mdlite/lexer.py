"""Stage 1: block-level lexer.

Turns a stream of source lines into a flat stream of tokens. The lexer is
the only place that knows about raw text lines; it is a small state machine
(needed so fenced code bodies are not re-interpreted as markup). It does
NOT build any document structure -- that is the parser's job.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional


@dataclass
class Token:
    kind: str            # blank|heading|fence_open|fence_close|code_line|
                         # quote|list_item|table_row|text
    text: str
    line: int            # 1-based source line
    col: int = 1         # 1-based column of the meaningful content
    data: object = None  # kind-specific payload (heading level, list indent...)


_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*(.*?)[ \t]*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,9}\.)[ \t]+(.*?)[ \t]*$")


def lex(lines: Iterable[str]) -> Iterator[Token]:
    """Yield block tokens for an iterable of raw lines (streaming)."""
    fence_char: Optional[str] = None
    fence_len = 0
    last_line = 0
    for lineno, raw in enumerate(lines, 1):
        last_line = lineno
        line = raw.rstrip("\r\n")
        if fence_char is not None:
            m = _FENCE_RE.match(line)
            if (
                m
                and m.group(1)[0] == fence_char
                and len(m.group(1)) >= fence_len
                and not m.group(2)
            ):
                fence_char = None
                yield Token("fence_close", "", lineno, 1)
            else:
                yield Token("code_line", line, lineno, 1)
            continue
        if not line.strip():
            yield Token("blank", "", lineno, 1)
            continue
        m = _FENCE_RE.match(line)
        if m:
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            col = line.index(m.group(1)) + 1
            yield Token("fence_open", m.group(2), lineno, col, fence_len)
            continue
        m = _HEADING_RE.match(line)
        if m:
            yield Token("heading", m.group(2), lineno, 1, len(m.group(1)))
            continue
        stripped = line.lstrip()
        if stripped.startswith(">"):
            col = len(line) - len(stripped) + 1
            text = stripped[1:]
            if text.startswith(" "):
                text = text[1:]
            yield Token("quote", text, lineno, col)
            continue
        m = _LIST_RE.match(line)
        if m:
            indent = len(m.group(1).expandtabs(2))
            yield Token(
                "list_item", m.group(3), lineno, indent + 1,
                (indent, m.group(2)),
            )
            continue
        if "|" in line:
            yield Token("table_row", line, lineno, 1)
            continue
        yield Token("text", line, lineno, 1)
