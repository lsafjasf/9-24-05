# mdlite — 安全的 Markdown 子集渲染库（纯标准库 Python 3）

面向内部文档站的离线渲染：防注入、错误带行列位置、大文档流式处理。

## 架构（分阶段，渲染只消费 AST）

```
源文本行流 ──> lexer.py（词法切分，产出 block token 流）
            ──> parser.py（结构解析，产出块级 AST；inline.py 做行内解析）
            ──> renderer.py（只消费 AST，输出 HTML）
```

- 词法与结构解析分离：lexer 是独立的状态机（围栏代码体不会被误当标记），
  parser 只读 token 流，renderer 只读 AST，全程无一处"正则替换拼 HTML"。
- 支持的语法：1–6 级标题、段落、`*强调*` / `**加粗**`、`` `行内代码` ``、
  ``` 与 ~~~ 围栏代码块、最多两层嵌套的有序/无序列表、引用、
  `[文字](链接)`、管道表格。
- 不支持的行内符号（`~~`、`__`、未闭合的 `*` 等）按普通文本原样输出；
  不支持的块语法（如无分隔行的"表格"）同样原样作为段落输出。

## 安全模型

- 所有文本经 `html.escape` 转义，所有属性值按带引号模式转义，
  输入中的 `<script>`、HTML 注释、事件属性等一律变成惰性文本。
- 链接协议白名单：`http` / `https` / `mailto` 及相对路径；
  `javascript:`、`data:`、`vbscript:`、协议相对 `//host` 一律拒绝
  （只渲染链接文字，不生成 `<a>`）。检测前会剥离控制字符与空白，
  大小写不敏感，防止 `java\tscript:` 之类绕过。
- 注入用例集：`tests/test_injection.py`（脚本标签、属性引号闭合、
  伪协议、注释内伪造标记等 20+ 断言）。

## 错误报告（不抛未捕获异常）

`render()` / `render_stream()` 返回错误列表，每项含 1-based 行列；
CLI 以 `文件:行:列: 消息` 输出到 stderr，退出码为 1。示例：

```
$ python3 -m mdlite examples/bad.md -o out.html
examples/bad.md:8:1: 表格列数不一致：表头 2 列，此行 3 列
examples/bad.md:12:5: 非法嵌套：列表最多支持 2 层，此处为第 3 层
examples/bad.md:14:1: 代码围栏未闭合（缺少结束的 ``` 行）
```

出错时仍会尽力渲染其余内容（未闭合围栏内容照常转义输出、
列数不符的行照常渲染、超深列表收敛到第二层）。

## 大文档与内存

`render_stream(lines, out)` 逐块流式处理：lexer 逐行产出 token，
parser 每次只物化一个块，renderer 立即写出后丢弃，内存占用由
"最大单个块"决定，与文档总大小无关。

实测（`tools/bench_memory.py`，Linux ru_maxrss，CPython 3.12）：

| 输入大小 | 流式峰值 RSS | 整读模式峰值 RSS |
|---------:|-------------:|----------------:|
| 40 MiB   | 13.4 MiB     | 236.0 MiB       |
| 80 MiB   | 33.8 MiB     | —               |
| 160 MiB  | 32.1 MiB     | —               |

流式模式峰值稳定在 ~32 MiB（Python 解释器基线 + 分配器驻留），
不随输入增长；整读模式随输入线性膨胀（40 MiB 输入即达 236 MiB），
仅供小文档的便捷 API `render()` 使用。吞吐约 6.5 MiB/s。

## 运行命令

```bash
# 自测（功能 + 注入 + 错误定位，共 39 例）
python3 -m unittest discover -s tests -v

# 渲染文件（错误输出到 stderr）
python3 -m mdlite input.md -o out.html

# 生成大文档并测内存
python3 tools/gen_big.py /tmp/big.md 40
python3 tools/bench_memory.py /tmp/big.md           # 流式
python3 tools/bench_memory.py /tmp/big.md --whole   # 整读对比
```

## 库 API

```python
from mdlite import render, render_stream

html, errors = render("# hello\n")        # 小文档
with open("big.md") as fin, open("big.html", "w") as fout:
    errors = render_stream(fin, fout)     # 大文档流式
for e in errors:
    print(e.line, e.col, e.message)
```
