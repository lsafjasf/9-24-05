"""Measure peak memory while rendering a large Markdown file.

Usage: python3 tools/bench_memory.py <big.md> [--whole]

  default     streaming render (render_stream), block at a time
  --whole     load entire input + output in memory (render())

Prints input size, wall time and peak RSS (ru_maxrss, Linux: KiB).
"""
import os
import resource
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mdlite import render, render_stream  # noqa: E402


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> None:
    path = sys.argv[1]
    whole = "--whole" in sys.argv
    size_mb = os.path.getsize(path) / 1024 / 1024
    t0 = time.perf_counter()
    if whole:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        html, errors = render(text)
        out_mb = len(html.encode("utf-8")) / 1024 / 1024
    else:
        with open(path, "r", encoding="utf-8") as fin, \
                open(os.devnull, "w", encoding="utf-8") as fout:
            errors = render_stream(fin, fout)
        out_mb = -1.0
    dt = time.perf_counter() - t0
    mode = "whole-buffer" if whole else "streaming"
    extra = f" output={out_mb:.1f} MiB" if whole else ""
    print(f"mode={mode} input={size_mb:.1f} MiB time={dt:.2f}s "
          f"peak_rss={peak_mb():.1f} MiB errors={len(errors)}{extra}")


if __name__ == "__main__":
    main()
