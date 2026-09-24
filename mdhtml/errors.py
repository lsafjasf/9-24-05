"""解析错误类型：携带行列位置，解析过程只收集不抛出。"""

from dataclasses import dataclass


@dataclass
class ParseError:
    line: int
    col: int
    message: str

    def __str__(self) -> str:
        return f"line {self.line}, col {self.col}: {self.message}"
