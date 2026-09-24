"""命令行入口：python -m mdhtml input.md [-o out.html]

解析错误输出到 stderr（文件:行:列: 消息），进程始终正常退出。
"""

import argparse
import sys

from . import iter_blocks, render_blocks
from .errors import ParseError


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mdhtml",
                                 description="Render a Markdown subset to safe HTML.")
    ap.add_argument("input", help="输入 Markdown 文件，'-' 表示标准输入")
    ap.add_argument("-o", "--output", help="输出 HTML 文件，缺省为标准输出")
    args = ap.parse_args(argv)

    errors = []
    close_out = False
    if args.output:
        out = open(args.output, "w", encoding="utf-8")
        close_out = True
    else:
        out = sys.stdout
    try:
        if args.input == "-":
            render_blocks(iter_blocks(sys.stdin, errors), out)
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                render_blocks(iter_blocks(f, errors), out)
    finally:
        if close_out:
            out.close()
    for err in errors:
        assert isinstance(err, ParseError)
        print(f"{args.input}:{err.line}:{err.col}: {err.message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
