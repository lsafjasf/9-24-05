"""Stage 3: renderer.

Consumes only the parser's AST (never raw source text) and writes HTML.
Every piece of text and every attribute value is escaped; link URLs go
through a protocol whitelist.
"""
from __future__ import annotations

import html
import re
from typing import Iterable, Optional, TextIO

from . import parser as ast
from .inline import Inline

ALLOWED_SCHEMES = frozenset({"http", "https", "mailto"})

_CONTROL_RE = re.compile(r"[\x00-\x20]+")
_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")


def sanitize_url(url: str) -> Optional[str]:
    """Return the URL if it is safe to put in href, else None."""
    cleaned = _CONTROL_RE.sub("", url)
    m = _SCHEME_RE.match(cleaned)
    if m:
        return url if m.group(1).lower() in ALLOWED_SCHEMES else None
    if cleaned.startswith("//"):
        return None
    return url


def esc_text(s: str) -> str:
    return html.escape(s, quote=False)


def esc_attr(s: str) -> str:
    return html.escape(s, quote=True)


def render_inlines(nodes: Iterable[Inline], out: TextIO) -> None:
    for node in nodes:
        kind = node.kind
        if kind == "text":
            out.write(esc_text(node.text))
        elif kind == "code":
            out.write("<code>" + esc_text(node.text) + "</code>")
        elif kind == "strong":
            out.write("<strong>")
            render_inlines(node.children, out)
            out.write("</strong>")
        elif kind == "em":
            out.write("<em>")
            render_inlines(node.children, out)
            out.write("</em>")
        elif kind == "link":
            url = sanitize_url(node.url or "")
            if url is None:
                # Unsafe protocol: render the label as plain text, no anchor.
                render_inlines(node.children, out)
            else:
                out.write('<a href="' + esc_attr(url)
                          + '" rel="nofollow noopener">')
                render_inlines(node.children, out)
                out.write("</a>")
        else:  # unknown inline node: degrade to escaped text
            out.write(esc_text(node.text))


def render_block(block: object, out: TextIO) -> None:
    if isinstance(block, ast.Heading):
        tag = f"h{block.level}"
        out.write(f"<{tag}>")
        render_inlines(block.children, out)
        out.write(f"</{tag}>\n")
    elif isinstance(block, ast.Paragraph):
        out.write("<p>")
        render_inlines(block.children, out)
        out.write("</p>\n")
    elif isinstance(block, ast.CodeBlock):
        out.write("<pre><code>")
        out.write(esc_text(block.text))
        out.write("</code></pre>\n")
    elif isinstance(block, ast.Quote):
        out.write("<blockquote>\n")
        for para in block.paragraphs:
            out.write("<p>")
            render_inlines(para, out)
            out.write("</p>\n")
        out.write("</blockquote>\n")
    elif isinstance(block, ast.ListBlock):
        _render_list(block, out)
    elif isinstance(block, ast.Table):
        _render_table(block, out)


def _render_list(block: ast.ListBlock, out: TextIO) -> None:
    tag = "ol" if block.ordered else "ul"
    out.write(f"<{tag}>\n")
    for item in block.items:
        out.write("<li>")
        render_inlines(item.children, out)
        for sub in item.sublists:
            out.write("\n")
            _render_list(sub, out)
        out.write("</li>\n")
    out.write(f"</{tag}>\n")


def _render_table(block: ast.Table, out: TextIO) -> None:
    out.write("<table>\n<thead>\n<tr>")
    for cell in block.header:
        out.write("<th>")
        render_inlines(cell, out)
        out.write("</th>")
    out.write("</tr>\n</thead>\n<tbody>\n")
    for row in block.rows:
        out.write("<tr>")
        for cell in row:
            out.write("<td>")
            render_inlines(cell, out)
            out.write("</td>")
        out.write("</tr>\n")
    out.write("</tbody>\n</table>\n")
