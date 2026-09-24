"""CLI: python3 -m mdlite input.md [-o out.html]

Reads the input as a stream, writes HTML, and prints any parse errors to
stderr as `file:line:col: message`. Exit code is 1 if errors were found.
"""
from __future__ import annotations

import argparse
import sys

from . import render_stream


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mdlite",
                                 description="Render Markdown subset to HTML")
    ap.add_argument("input", help="input markdown file ('-' for stdin)")
    ap.add_argument("-o", "--output", help="output HTML file (default stdout)")
    args = ap.parse_args(argv)

    if args.input == "-":
        fin = sys.stdin
        name = "<stdin>"
    else:
        fin = open(args.input, "r", encoding="utf-8")
        name = args.input

    fout = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        errors = render_stream(fin, fout)
    finally:
        if fin is not sys.stdin:
            fin.close()
        if fout is not sys.stdout:
            fout.close()

    for err in errors:
        print(f"{name}:{err}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
