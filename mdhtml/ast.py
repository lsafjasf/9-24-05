"""解析层输出的 AST 节点定义。渲染层只消费这些节点。"""


class Node:
    __slots__ = ("line",)

    def __init__(self, line):
        self.line = line


# ---- 块级节点 ----

class Heading(Node):
    __slots__ = ("level", "children")

    def __init__(self, level, children, line):
        super().__init__(line)
        self.level = level
        self.children = children  # 行内节点列表


class Paragraph(Node):
    __slots__ = ("children",)

    def __init__(self, children, line):
        super().__init__(line)
        self.children = children


class CodeBlock(Node):
    __slots__ = ("code", "lang")

    def __init__(self, code, lang, line):
        super().__init__(line)
        self.code = code
        self.lang = lang


class Quote(Node):
    __slots__ = ("blocks",)

    def __init__(self, blocks, line):
        super().__init__(line)
        self.blocks = blocks  # Paragraph 列表


class ListBlock(Node):
    __slots__ = ("ordered", "items")

    def __init__(self, ordered, line):
        super().__init__(line)
        self.ordered = ordered
        self.items = []  # ListItem 列表


class ListItem(Node):
    __slots__ = ("content", "children")

    def __init__(self, content, children, line):
        super().__init__(line)
        self.content = content    # 行内节点列表
        self.children = children  # 嵌套块（子列表或降级段落）


class Table(Node):
    __slots__ = ("headers", "rows")

    def __init__(self, headers, rows, line):
        super().__init__(line)
        self.headers = headers  # 每格为行内节点列表
        self.rows = rows        # 每行为格子列表


# ---- 行内节点 ----

class Inline:
    __slots__ = ()


class Text(Inline):
    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text


class Code(Inline):
    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text


class Em(Inline):
    __slots__ = ("children",)

    def __init__(self, children):
        self.children = children


class Strong(Inline):
    __slots__ = ("children",)

    def __init__(self, children):
        self.children = children


class Link(Inline):
    __slots__ = ("children", "url")

    def __init__(self, children, url):
        self.children = children
        self.url = url
