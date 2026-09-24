"""行内解析：字符级扫描器（非正则替换链）。

支持：*强调*、**加粗**、`行内代码`、[文本](链接)。
未闭合或不认识的符号按字面文本保留，交由渲染层转义输出。
"""

from . import ast


def parse_inlines(text, line=0, errors=None):
    nodes, _ = _parse(text, line)
    return nodes


def _parse(text, line):
    nodes = []
    buf = []
    i = 0
    n = len(text)

    def flush():
        if buf:
            nodes.append(ast.Text("".join(buf)))
            buf.clear()

    while i < n:
        ch = text[i]
        if ch == "`":
            j = text.find("`", i + 1)
            if j != -1 and j > i + 1:
                flush()
                nodes.append(ast.Code(text[i + 1:j]))
                i = j + 1
                continue
            buf.append(ch)
            i += 1
        elif ch == "*":
            if text.startswith("**", i):
                j = text.find("**", i + 2)
                if j != -1 and j > i + 2:
                    flush()
                    children, _ = _parse(text[i + 2:j], line)
                    nodes.append(ast.Strong(children))
                    i = j + 2
                    continue
                buf.append("*")
                i += 1
            else:
                j = text.find("*", i + 1)
                if j != -1 and j > i + 1:
                    flush()
                    children, _ = _parse(text[i + 1:j], line)
                    nodes.append(ast.Em(children))
                    i = j + 1
                    continue
                buf.append("*")
                i += 1
        elif ch == "[":
            m = _match_link(text, i, line)
            if m is not None:
                label_nodes, url, end = m
                flush()
                nodes.append(ast.Link(label_nodes, url))
                i = end
            else:
                buf.append("[")
                i += 1
        else:
            buf.append(ch)
            i += 1
    flush()
    return nodes, i


def _match_link(text, i, line):
    """从 text[i] == '[' 起尝试匹配 [label](url)。失败返回 None。"""
    if i > 0 and text[i - 1] == "!":
        return None  # 图片语法不支持，整体按普通文本输出
    j = text.find("]", i + 1)
    if j == -1:
        return None
    label = text[i + 1:j]
    k = j + 1
    if k >= len(text) or text[k] != "(":
        return None
    e = text.find(")", k + 1)
    if e == -1:
        return None
    url = text[k + 1:e].strip()
    if any(c in url for c in " \t\r\n"):
        return None
    label_nodes, _ = _parse(label, line)
    return label_nodes, url, e + 1
