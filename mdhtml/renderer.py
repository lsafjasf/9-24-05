"""渲染层：只消费 AST，输出 HTML。

安全策略：
- 所有文本节点经 html.escape 转义；
- 所有属性值（href、class）同样转义，引号无法闭合属性；
- 链接协议白名单：http/https/mailto 及相对路径，其余（javascript:、
  data:、vbscript:、协议相对 // 等）一律剥离 href，仅保留链接文本。
"""

import html
import re

from . import ast

_ALLOWED_SCHEMES = {"http", "https", "mailto"}
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_STRIP_RE = re.compile(r"[\x00-\x20\x7f]+")


def safe_href(url):
    """返回可安全使用的 href；协议不在白名单则返回 None。"""
    cleaned = _STRIP_RE.sub("", url)  # 浏览器会忽略协议名中的空白/控制符
    m = _SCHEME_RE.match(cleaned)
    if m:
        return url if m.group(1).lower() in _ALLOWED_SCHEMES else None
    if cleaned.startswith("//"):
        return None
    return url


def esc(text):
    return html.escape(text, quote=True)


def render_blocks(blocks, out):
    for block in blocks:
        _render_block(block, out)


def _render_block(node, out):
    if isinstance(node, ast.Heading):
        out.write(f"<h{node.level}>")
        _render_inlines(node.children, out)
        out.write(f"</h{node.level}>\n")
    elif isinstance(node, ast.Paragraph):
        out.write("<p>")
        _render_inlines(node.children, out)
        out.write("</p>\n")
    elif isinstance(node, ast.CodeBlock):
        if node.lang:
            out.write(f'<pre><code class="language-{esc(node.lang)}">')
        else:
            out.write("<pre><code>")
        out.write(esc(node.code))
        out.write("</code></pre>\n")
    elif isinstance(node, ast.Quote):
        out.write("<blockquote>\n")
        for b in node.blocks:
            _render_block(b, out)
        out.write("</blockquote>\n")
    elif isinstance(node, ast.ListBlock):
        tag = "ol" if node.ordered else "ul"
        out.write(f"<{tag}>\n")
        for item in node.items:
            out.write("<li>")
            _render_inlines(item.content, out)
            for child in item.children:
                out.write("\n")
                _render_block(child, out)
            out.write("</li>\n")
        out.write(f"</{tag}>\n")
    elif isinstance(node, ast.Table):
        out.write("<table>\n<thead><tr>")
        for cell in node.headers:
            out.write("<th>")
            _render_inlines(cell, out)
            out.write("</th>")
        out.write("</tr></thead>\n<tbody>\n")
        for row in node.rows:
            out.write("<tr>")
            for cell in row:
                out.write("<td>")
                _render_inlines(cell, out)
                out.write("</td>")
            out.write("</tr>\n")
        out.write("</tbody></table>\n")
    else:  # 未知节点不输出，也不抛异常
        pass


def _render_inlines(nodes, out):
    for node in nodes:
        if isinstance(node, ast.Text):
            out.write(esc(node.text))
        elif isinstance(node, ast.Code):
            out.write("<code>")
            out.write(esc(node.text))
            out.write("</code>")
        elif isinstance(node, ast.Em):
            out.write("<em>")
            _render_inlines(node.children, out)
            out.write("</em>")
        elif isinstance(node, ast.Strong):
            out.write("<strong>")
            _render_inlines(node.children, out)
            out.write("</strong>")
        elif isinstance(node, ast.Link):
            href = safe_href(node.url)
            if href is None:
                out.write("<a>")
            else:
                out.write(f'<a href="{esc(href)}">')
            _render_inlines(node.children, out)
            out.write("</a>")
