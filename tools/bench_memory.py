"""Measure peak memory while rendering a large Markdown file.

Usage: python3 tools/bench_memory.py <big.md> [--whole]

  default     streaming render (render_stream), block at a time
  --whole     load entire input + output in memory (render())

Prints input size, wall time and peak memory. The peak is measured with
the best backend the platform offers: ru_maxrss via ``resource`` on
Unix, GetProcessMemoryInfo on Windows, and tracemalloc (Python heap
only) as a last-resort fallback. The backend used is printed so numbers
from different platforms are not compared by mistake.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mdlite import render, render_stream  # noqa: E402


def _make_peak_meter():
    """Return (start, read) for peak-memory measurement.

    start() arms the meter (only needed by the tracemalloc fallback);
    read() returns (peak_mib, label) where label names the backend.
    """
    try:
        import resource
    except ImportError:
        pass
    else:
        def read():
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Linux reports KiB, macOS reports bytes.
            scale = 1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0
            return rss / scale, "peak_rss(ru_maxrss)"
        return lambda: None, read

    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes

        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        def read():
            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(counters), counters.cb)
            return (counters.PeakWorkingSetSize / (1024.0 * 1024.0),
                    "peak_rss(PeakWorkingSetSize)")
        return lambda: None, read

    import tracemalloc

    def read():
        _, peak = tracemalloc.get_traced_memory()
        return peak / (1024.0 * 1024.0), "peak_pyheap(tracemalloc)"
    return tracemalloc.start, read


def main() -> None:
    path = sys.argv[1]
    whole = "--whole" in sys.argv
    size_mb = os.path.getsize(path) / 1024 / 1024
    start_meter, read_peak = _make_peak_meter()
    start_meter()
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
    peak_mb, label = read_peak()
    mode = "whole-buffer" if whole else "streaming"
    extra = f" output={out_mb:.1f} MiB" if whole else ""
    print(f"mode={mode} input={size_mb:.1f} MiB time={dt:.2f}s "
          f"{label}={peak_mb:.1f} MiB errors={len(errors)}{extra}")


if __name__ == "__main__":
    main()
