"""词法层：把输入行流切分为行级 token。

输入是任意字符串可迭代对象（可流式读取大文件），
输出 Token 流。每个 token 保留原始行文本（raw）与行号，
供解析层定位错误与还原代码块内容。
"""

import re
from typing import Iterable, Iterator

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
_QUOTE_RE = re.compile(r"^[ \t]*>[ \t]?(.*)$")
_LIST_RE = re.compile(r"^( *)([-*+]|\d{1,9}[.)])[ \t]+(.*)$")


class Token:
    __slots__ = ("kind", "line", "col", "text", "raw", "indent", "level", "ordered")

    def __init__(self, kind, line, col, text, raw, indent=0, level=0, ordered=False):
        self.kind = kind          # blank/heading/fence/quote/list_item/text
        self.line = line          # 1 起始行号
        self.col = col            # 1 起始列号（token 关键字符位置）
        self.text = text          # 去掉标记后的正文
        self.raw = raw            # 原始行（不含换行符）
        self.indent = indent      # list_item 的前导空格数
        self.level = level        # heading 的级别
        self.ordered = ordered    # list_item 是否有序

    def __repr__(self):
        return f"Token({self.kind!r}, line={self.line}, text={self.text!r})"


def lex(lines: Iterable[str]) -> Iterator[Token]:
    for lineno, raw in enumerate(lines, 1):
        raw = raw.rstrip("\n").rstrip("\r")
        stripped = raw.strip()
        if not stripped:
            yield Token("blank", lineno, 1, "", raw)
            continue
        m = _FENCE_RE.match(raw)
        if m:
            indent, _marker, info = m.groups()
            yield Token("fence", lineno, len(indent) + 1, info.strip(), raw)
            continue
        m = _HEADING_RE.match(raw)
        if m:
            hashes, text = m.groups()
            yield Token("heading", lineno, 1, text, raw, level=len(hashes))
            continue
        m = _QUOTE_RE.match(raw)
        if m:
            yield Token("quote", lineno, raw.index(">") + 1, m.group(1), raw)
            continue
        m = _LIST_RE.match(raw)
        if m:
            indent, marker, text = m.groups()
            ordered = marker[0].isdigit()
            yield Token("list_item", lineno, len(indent) + 1, text, raw,
                        indent=len(indent), ordered=ordered)
            continue
        yield Token("text", lineno, 1, raw, raw)
