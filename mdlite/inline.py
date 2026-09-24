"""Inline-level parser: emphasis, inline code, links.

This is a small hand-written scanner (no regex substitution against the
output HTML). Anything that is not recognised is kept as literal text, so
unsupported inline syntax passes through untouched.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Inline:
    kind: str                      # text|code|strong|em|link
    text: str = ""
    children: List["Inline"] = field(default_factory=list)
    url: Optional[str] = None
    line: int = 1
    col: int = 1


def parse_inlines(text: str, line: int = 1, base_col: int = 1) -> List[Inline]:
    nodes: List[Inline] = []
    buf: List[str] = []
    buf_col = base_col

    def flush(upto: int) -> None:
        nonlocal buf, buf_col
        if buf:
            nodes.append(Inline("text", "".join(buf), line=line, col=buf_col))
            buf = []
        buf_col = base_col + upto + 1

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "`":
            j = text.find("`", i + 1)
            if j != -1:
                flush(i)
                nodes.append(Inline("code", text[i + 1:j],
                                    line=line, col=base_col + i))
                i = j + 1
                continue
            buf.append("`")
            i += 1
            continue
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j != -1 and j > i + 2:
                flush(i)
                children = parse_inlines(text[i + 2:j], line, base_col + i + 2)
                nodes.append(Inline("strong", children=children,
                                    line=line, col=base_col + i))
                i = j + 2
                continue
            buf.append("**")
            i += 2
            continue
        if ch == "*":
            j = text.find("*", i + 1)
            if j != -1 and j > i + 1:
                flush(i)
                children = parse_inlines(text[i + 1:j], line, base_col + i + 1)
                nodes.append(Inline("em", children=children,
                                    line=line, col=base_col + i))
                i = j + 1
                continue
            buf.append("*")
            i += 1
            continue
        if ch == "[":
            close = text.find("](", i + 1)
            if close != -1:
                end = text.find(")", close + 2)
                if end != -1:
                    flush(i)
                    label = text[i + 1:close]
                    url = text[close + 2:end].strip()
                    children = parse_inlines(label, line, base_col + i + 1)
                    nodes.append(Inline("link", children=children, url=url,
                                        line=line, col=base_col + i))
                    i = end + 1
                    continue
            buf.append("[")
            i += 1
            continue
        buf.append(ch)
        i += 1
    flush(n)
    return nodes
