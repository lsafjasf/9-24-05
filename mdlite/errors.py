"""Error type carrying source position (line/col, 1-based)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarkdownError:
    message: str
    line: int
    col: int = 1

    def __str__(self) -> str:
        return f"{self.line}:{self.col}: {self.message}"
