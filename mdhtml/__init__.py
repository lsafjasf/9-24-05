"""mdhtml：Markdown 子集 -> HTML 的离线安全渲染库（仅标准库）。

分层：lexer（词法切分） -> parser（结构解析，逐块产出 AST）
      -> renderer（只消费 AST，全量转义 + 链接协议白名单）。
"""

import io
from dataclasses import dataclass, field
from typing import Iterable, List, TextIO

from .errors import ParseError
from .parser import iter_blocks
from .renderer import render_blocks, safe_href

__all__ = ["ParseError", "RenderResult", "render_markdown", "render_lines",
           "iter_blocks", "render_blocks", "safe_href"]

__version__ = "0.1.0"


@dataclass
class RenderResult:
    html: str
    errors: List[ParseError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def render_markdown(text: str) -> RenderResult:
    """一次性渲染字符串，返回 HTML 与错误列表（含行列号）。"""
    errors: List[ParseError] = []
    out = io.StringIO()
    render_blocks(iter_blocks(text.splitlines(), errors), out)
    return RenderResult(out.getvalue(), errors)


def render_lines(lines: Iterable[str], out: TextIO) -> List[ParseError]:
    """流式渲染：逐行读取、逐块写出，内存占用与文档大小无关。"""
    errors: List[ParseError] = []
    render_blocks(iter_blocks(lines, errors), out)
    return errors
