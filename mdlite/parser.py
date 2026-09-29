"""Stage 2: structural parser.

Consumes the lexer's token stream and produces a block-level AST. The
parser never emits HTML. Recoverable problems (unclosed fence, ragged
table rows, list nesting deeper than two levels) are recorded as
MarkdownError objects with line/col positions; parsing always continues.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple

from .errors import MarkdownError
from .inline import Inline, parse_inlines
from .lexer import Token

MAX_LIST_DEPTH = 2


# ---------------------------------------------------------------- AST nodes

@dataclass
class Heading:
    level: int
    children: List[Inline]
    line: int


@dataclass
class Paragraph:
    children: List[Inline]
    line: int


@dataclass
class CodeBlock:
    text: str
    info: str
    line: int


@dataclass
class Quote:
    paragraphs: List[List[Inline]]
    line: int


@dataclass
class ListItem:
    children: List[Inline]
    sublists: List["ListBlock"] = field(default_factory=list)


@dataclass
class ListBlock:
    ordered: bool
    items: List[ListItem]
    line: int


@dataclass
class Table:
    header: List[List[Inline]]
    rows: List[List[List[Inline]]]
    line: int


# ---------------------------------------------------------------- helpers

_DELIM_CELL_RE = re.compile(r"^:?-+:?$")


def split_cells(text: str) -> List[str]:
    t = text.strip()
    if t.startswith("|"):
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    return [c.strip() for c in t.split("|")]


def _is_delim_row(cells: List[str]) -> bool:
    return bool(cells) and all(_DELIM_CELL_RE.match(c or "") for c in cells)


def _cell_col(text: str, index: int) -> int:
    """1-based column where cell `index` (0-based) starts in the raw row.

    If the row has no such cell (missing trailing cells), returns the
    position where that cell would begin, i.e. just past the row content.
    """
    t = text.strip()
    offset = len(text) - len(text.lstrip())
    if t.startswith("|"):
        offset += 1
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    pos = 0
    for i, seg in enumerate(t.split("|")):
        if i == index:
            return offset + pos + (len(seg) - len(seg.lstrip())) + 1
        pos += len(seg) + 1
    return offset + len(t) + 1


class _Stream:
    """One-token pushback wrapper around the token iterator."""

    def __init__(self, tokens: Iterator[Token]):
        self._it = tokens
        self._buf: List[Token] = []

    def next(self) -> Optional[Token]:
        if self._buf:
            return self._buf.pop()
        return next(self._it, None)

    def push(self, tok: Token) -> None:
        self._buf.append(tok)


# ---------------------------------------------------------------- parser

def iter_blocks(
    tokens: Iterator[Token], errors: List[MarkdownError]
) -> Iterator[object]:
    """Yield top-level blocks one at a time (streaming friendly)."""
    stream = _Stream(tokens)
    while True:
        tok = stream.next()
        if tok is None:
            return
        kind = tok.kind
        if kind == "blank":
            continue
        if kind == "heading":
            yield Heading(tok.data, parse_inlines(tok.text, tok.line), tok.line)
        elif kind == "fence_open":
            yield _parse_code_block(stream, tok, errors)
        elif kind == "quote":
            yield _parse_quote(stream, tok)
        elif kind == "list_item":
            yield _parse_list(stream, tok, errors)
        elif kind == "table_row":
            yield _parse_table(stream, tok, errors)
        elif kind == "fence_close":
            errors.append(MarkdownError(
                "孤立的代码围栏结束标记（没有对应的开始标记）", tok.line, tok.col))
            yield Paragraph([Inline("text", "```", line=tok.line, col=tok.col)],
                            tok.line)
        else:  # text
            yield _parse_paragraph(stream, tok)


def _parse_paragraph(stream: _Stream, first: Token) -> Paragraph:
    lines = [first.text]
    while True:
        tok = stream.next()
        if tok is None or tok.kind != "text":
            if tok is not None:
                stream.push(tok)
            break
        lines.append(tok.text)
    return Paragraph(parse_inlines("\n".join(lines), first.line), first.line)


def _parse_code_block(
    stream: _Stream, open_tok: Token, errors: List[MarkdownError]
) -> CodeBlock:
    body: List[str] = []
    while True:
        tok = stream.next()
        if tok is None:
            errors.append(MarkdownError(
                "代码围栏未闭合（缺少结束的 ``` 行）",
                open_tok.line, open_tok.col))
            break
        if tok.kind == "fence_close":
            break
        body.append(tok.text)
    return CodeBlock("\n".join(body), open_tok.text, open_tok.line)


def _parse_quote(stream: _Stream, first: Token) -> Quote:
    lines = [first.text]
    while True:
        tok = stream.next()
        if tok is None or tok.kind != "quote":
            if tok is not None:
                stream.push(tok)
            break
        lines.append(tok.text)
    paragraphs: List[List[Inline]] = []
    current: List[str] = []
    for ln in lines:
        if ln.strip():
            current.append(ln)
        elif current:
            paragraphs.append(parse_inlines("\n".join(current), first.line))
            current = []
    if current:
        paragraphs.append(parse_inlines("\n".join(current), first.line))
    return Quote(paragraphs, first.line)


def _parse_list(
    stream: _Stream, first: Token, errors: List[MarkdownError]
) -> ListBlock:
    toks = [first]
    while True:
        tok = stream.next()
        if tok is None or tok.kind != "list_item":
            if tok is not None:
                stream.push(tok)
            break
        toks.append(tok)

    root = ListBlock(ordered=toks[0].data[1].endswith("."), items=[],
                     line=first.line)
    # stack of (depth, list); depth 1 == root
    stack: List[Tuple[int, ListBlock]] = [(1, root)]
    for tok in toks:
        indent, marker = tok.data
        depth = indent // 2 + 1
        if depth > MAX_LIST_DEPTH:
            errors.append(MarkdownError(
                f"非法嵌套：列表最多支持 {MAX_LIST_DEPTH} 层，"
                f"此处为第 {depth} 层", tok.line, tok.col))
            depth = MAX_LIST_DEPTH
        item = ListItem(children=parse_inlines(tok.text, tok.line,
                                               tok.col + len(marker) + 1))
        while len(stack) > depth:
            stack.pop()
        while len(stack) < depth:
            parent = stack[-1][1]
            if not parent.items:
                break  # nothing to nest under; keep at current depth
            child = ListBlock(ordered=marker.endswith("."), items=[],
                              line=tok.line)
            parent.items[-1].sublists.append(child)
            stack.append((len(stack) + 1, child))
        stack[-1][1].items.append(item)
    return root


def _parse_table(
    stream: _Stream, first: Token, errors: List[MarkdownError]
) -> object:
    toks = [first]
    while True:
        tok = stream.next()
        if tok is None or tok.kind != "table_row":
            if tok is not None:
                stream.push(tok)
            break
        toks.append(tok)

    if len(toks) < 2 or not _is_delim_row(split_cells(toks[1].text)):
        # Not actually a table: unsupported syntax -> plain paragraph text.
        joined = "\n".join(t.text for t in toks)
        return Paragraph(parse_inlines(joined, first.line), first.line)

    header_cells = split_cells(toks[0].text)
    width = len(header_cells)
    header = [parse_inlines(c, toks[0].line) for c in header_cells]
    rows: List[List[List[Inline]]] = []
    for tok in toks[2:]:
        cells = split_cells(tok.text)
        if len(cells) != width:
            if len(cells) > width:
                col = _cell_col(tok.text, width)
                detail = f"第 {width + 1} 列「{cells[width]}」为多出内容"
            else:
                col = _cell_col(tok.text, len(cells))
                detail = f"缺少第 {len(cells) + 1} 列"
            errors.append(MarkdownError(
                f"表格列数不一致：表头 {width} 列，此行 {len(cells)} 列"
                f"（{detail}）", tok.line, col))
        rows.append([parse_inlines(c, tok.line) for c in cells])
    return Table(header, rows, first.line)
