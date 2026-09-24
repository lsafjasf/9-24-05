"""内存基准：生成大文档，分别测量流式与一次性渲染的内存峰值。

用法：python3 bench/memory_bench.py [目标大小MB]
"""

import io
import os
import resource
import sys
import tempfile
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mdhtml import render_lines, render_markdown

CHUNK = """# 性能测试章节

这是一段普通文本，包含 *强调*、**加粗**、`行内代码` 与 [链接](https://example.com)。

- 列表项一
- 列表项二
    - 嵌套项甲
    - 嵌套项乙

> 引用一段文字，跨两行
> 的第二行。

| 列甲 | 列乙 | 列丙 |
| --- | --- | --- |
| a1 | b1 | c1 |
| a2 | b2 | c2 |

```python
def f(x):
    return x < 1
```

"""


def generate(path, target_mb):
    target = target_mb * 1024 * 1024
    written = 0
    with open(path, "w", encoding="utf-8") as f:
        while written < target:
            f.write(CHUNK)
            written += len(CHUNK.encode("utf-8"))
    return written


def peak_of(fn):
    tracemalloc.start()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main():
    target_mb = float(sys.argv[1]) if len(sys.argv) > 1 else 32
    tmpdir = tempfile.mkdtemp(prefix="mdhtml_bench_")
    src = os.path.join(tmpdir, "big.md")
    dst = os.path.join(tmpdir, "big.html")
    size = generate(src, target_mb)
    print(f"输入文件: {src}  ({size / 1024 / 1024:.1f} MiB)")

    def run_streaming():
        with open(src, encoding="utf-8") as fin, \
                open(dst, "w", encoding="utf-8") as fout:
            errors = render_lines(fin, fout)
        assert not errors

    def run_oneshot():
        with open(src, encoding="utf-8") as fin:
            text = fin.read()
        result = render_markdown(text)
        assert result.ok

    peak_stream = peak_of(run_streaming)
    out_size = os.path.getsize(dst)
    peak_oneshot = peak_of(run_oneshot)
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    print(f"输出文件: {out_size / 1024 / 1024:.1f} MiB")
    print(f"流式渲染  Python 堆峰值: {peak_stream / 1024 / 1024:.2f} MiB")
    print(f"一次性渲染 Python 堆峰值: {peak_oneshot / 1024 / 1024:.2f} MiB")
    print(f"进程 RSS 峰值: {rss_mb:.1f} MiB")


if __name__ == "__main__":
    main()
