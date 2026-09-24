"""结构解析层：消费 lexer 的 token 流，逐块产出 AST。

采用生成器逐块输出，配合渲染层可实现恒定内存的流式处理：
任意时刻内存中只保留当前块（段落/表格/列表等），而非整棵语法树。
所有解析错误记录到 errors 列表（含行列号），不抛异常。
"""

import re
from typing import Iterable, Iterator, List

from . import ast
from .errors import ParseError
from .inline import parse_inlines
from .lexer import lex

_DELIM_CELL_RE = re.compile(r"^:?-+:?$")

MAX_LIST_INDENT = 8  # 0-3 第一层，4-7 第二层，>=8 视为非法嵌套


class _Peekable:
    """带前瞻的 token 迭代器（表格需要向前看一行）。"""

    def __init__(self, it):
        self._it = iter(it)
        self._buf = []

    def peek(self, n=0):
        while len(self._buf) <= n:
            try:
                self._buf.append(next(self._it))
            except StopIteration:
                return None
        return self._buf[n]

    def next(self):
        if self._buf:
            return self._buf.pop(0)
        return next(self._it, None)


def iter_blocks(lines: Iterable[str], errors: List[ParseError]) -> Iterator[ast.Node]:
    """逐块解析。lines 可以是文件对象等惰性行流。"""
    toks = _Peekable(lex(lines))
    while True:
        tok = toks.peek()
        if tok is None:
            return
        if tok.kind == "blank":
            toks.next()
            continue
        if tok.kind == "heading":
            toks.next()
            yield ast.Heading(tok.level, parse_inlines(tok.text, tok.line, errors), tok.line)
        elif tok.kind == "fence":
            yield _parse_fence(toks, errors)
        elif tok.kind == "quote":
            yield _parse_quote(toks, errors)
        elif tok.kind == "list_item":
            yield _parse_list(toks, errors, level=1)
        elif tok.kind == "text":
            nxt = toks.peek(1)
            if "|" in tok.text and nxt is not None and nxt.kind == "text" \
                    and _is_delim_row(nxt.text):
                yield _parse_table(toks, errors)
            else:
                yield _parse_paragraph(toks, errors)


def _parse_paragraph(toks, errors):
    first = toks.peek()
    parts = []
    while True:
        tok = toks.peek()
        if tok is None or tok.kind != "text":
            break
        parts.append(toks.next().text)
    text = "\n".join(parts)
    return ast.Paragraph(parse_inlines(text, first.line, errors), first.line)


def _parse_fence(toks, errors):
    open_tok = toks.next()
    info = open_tok.text.strip()
    lang = info.split()[0] if info else ""
    buf = []
    while True:
        tok = toks.next()
        if tok is None:
            errors.append(ParseError(open_tok.line, open_tok.col,
                                     "未闭合的代码围栏"))
            break
        if tok.kind == "fence":
            break
        buf.append(tok.raw)
    return ast.CodeBlock("\n".join(buf), lang, open_tok.line)


def _parse_quote(toks, errors):
    start = toks.peek().line
    qlines = []
    while True:
        tok = toks.peek()
        if tok is None or tok.kind != "quote":
            break
        qlines.append(toks.next().text)
    paras, cur = [], []
    for text in qlines:
        if text.strip() == "":
            if cur:
                paras.append("\n".join(cur))
                cur = []
        else:
            cur.append(text)
    if cur:
        paras.append("\n".join(cur))
    blocks = [ast.Paragraph(parse_inlines(p, start, errors), start) for p in paras]
    return ast.Quote(blocks, start)


def _item_level(indent):
    if indent < 4:
        return 1
    if indent < MAX_LIST_INDENT:
        return 2
    return 3


def _parse_list(toks, errors, level):
    first = toks.peek()
    lst = ast.ListBlock(first.ordered, first.line)
    while True:
        tok = toks.peek()
        if tok is None or tok.kind != "list_item":
            break
        item_level = _item_level(tok.indent)
        if item_level <= level - 1:
            break  # 缩进回退，交还给上层列表
        if item_level == level:
            toks.next()
            lst.items.append(ast.ListItem(
                parse_inlines(tok.text, tok.line, errors), [], tok.line))
            continue
        if item_level == level + 1 and level < 2:
            if not lst.items:
                errors.append(ParseError(tok.line, tok.indent + 1,
                                         "非法嵌套：子列表缺少父级列表项"))
                toks.next()
                lst.items.append(ast.ListItem(
                    parse_inlines(tok.text, tok.line, errors), [], tok.line))
                continue
            child = _parse_list(toks, errors, level + 1)
            lst.items[-1].children.append(child)
            continue
        # 嵌套超过两层：报错并降级为父项内的普通文本
        errors.append(ParseError(tok.line, tok.indent + 1,
                                 "非法嵌套：列表最多支持两层"))
        toks.next()
        if lst.items:
            lst.items[-1].children.append(
                ast.Paragraph([ast.Text(tok.text)], tok.line))
    return lst


def _split_row(text):
    s = text.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_delim_row(text):
    if "-" not in text:
        return False
    cells = _split_row(text)
    return bool(cells) and all(_DELIM_CELL_RE.match(c) for c in cells)


def _diverge_col(raw, expected):
    """定位列数分叉处：多出时指向第 expected+1 个单元格，缺失时指向行尾。"""
    pos = -1
    for _ in range(expected):
        pos = raw.find("|", pos + 1)
        if pos == -1:
            return len(raw) + 1
    return pos + 2 if pos != -1 else len(raw) + 1


def _parse_table(toks, errors):
    header_tok = toks.next()
    headers = _split_row(header_tok.text)
    toks.next()  # 分隔行
    header_cells = [parse_inlines(h, header_tok.line, errors) for h in headers]
    rows = []
    while True:
        tok = toks.peek()
        if tok is None or tok.kind != "text" or "|" not in tok.text:
            break
        toks.next()
        cells = _split_row(tok.text)
        if len(cells) != len(headers):
            col = _diverge_col(tok.raw, len(headers))
            errors.append(ParseError(
                tok.line, col,
                f"表格列数不一致：表头 {len(headers)} 列，本行 {len(cells)} 列"))
            if len(cells) < len(headers):
                cells += [""] * (len(headers) - len(cells))
            else:
                cells = cells[:len(headers)]
        rows.append([parse_inlines(c, tok.line, errors) for c in cells])
    return ast.Table(header_cells, rows, header_tok.line)
