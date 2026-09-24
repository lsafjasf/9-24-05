"""Generate a large mixed Markdown document for memory benchmarking.

Usage: python3 tools/gen_big.py <output.md> <target_mb>
"""
import sys

BLOCK = """\
## Section {i} <script>alert('xss')</script>

A paragraph with *emphasis*, **strong**, `inline <code>` and a
[link](https://example.com/page?a=1&b=2) plus an [evil](javascript:alert(1))
one. Some raw <b>HTML</b> & entities -- passed through as text.

```python
def f(x):
    return "<script>alert(%d)</script>" % x
```

> A quote with <img src=x onerror=alert(1)> inside.

- item one
- item two
  - nested a
  - nested b
- item three

| col1 | col2 | col3 |
|------|------|------|
| <a>  | b    | c    |
| d    | e    | f    |

"""


def main() -> None:
    path, target_mb = sys.argv[1], float(sys.argv[2])
    target = int(target_mb * 1024 * 1024)
    written = 0
    i = 0
    with open(path, "w", encoding="utf-8") as f:
        while written < target:
            chunk = BLOCK.format(i=i)
            f.write(chunk)
            written += len(chunk.encode("utf-8"))
            i += 1
    print(f"wrote {written / 1024 / 1024:.1f} MiB to {path}")


if __name__ == "__main__":
    main()
