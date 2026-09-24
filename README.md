# mdhtml：Markdown 子集 -> HTML 的安全离线渲染库

纯 Python 3 标准库实现，面向内部文档站离线渲染用户提交内容：
默认全量转义防注入，解析错误带行列号，大文档可流式处理。

## 架构（分阶段，非正则替换链）

```
行流 ──> lexer.py   词法切分：行 -> Token（标题/围栏/引用/列表项/文本…）
           │
           ▼
         parser.py  结构解析：Token 流 -> AST（逐块产出，生成器）
           │        行内由 inline.py 的字符扫描器处理（强调/代码/链接）
           ▼
         renderer.py 渲染：只消费 AST，文本与属性一律 html.escape，
                      链接走协议白名单（http/https/mailto/相对路径）
```

解析错误收集进 `errors` 列表（`ParseError(line, col, message)`），
全程不抛未捕获异常，出错块做 best-effort 渲染。

## 支持的语法

标题（1-6 级）、段落、`*强调*`、`**加粗**`、`行内代码`、围栏代码块、
两层嵌套列表（有序/无序）、引用、链接、表格。
不支持的语法（图片、删除线、七级标题等）按普通文本原样转义输出。

## 安全策略

- 所有文本节点与属性值经 `html.escape(quote=True)` 转义；
- 链接协议白名单：`http`/`https`/`mailto`/相对路径；
  `javascript:`、`data:`、`vbscript:`、协议相对 `//` 一律剥离 `href`；
- 检查前剔除 URL 中的空白与控制字符，防 `java<TAB>script:` 绕过；
- HTML 注释不特殊处理，整体转义，注释内伪造标记无法穿透。

## 使用

```bash
# 一次性渲染（库）
python3 -c "from mdhtml import render_markdown; r = render_markdown(open('doc.md').read()); print(r.html); print(r.errors)"

# CLI（流式，恒定内存；错误输出到 stderr：文件:行:列: 消息）
python3 -m mdhtml input.md -o out.html

# 测试
python3 -m unittest discover -s tests -v

# 内存基准（参数为目标 MiB，默认 32）
python3 bench/memory_bench.py 32
```

流式 API：`mdhtml.render_lines(lines, out)`，逐行读、逐块写，
任意时刻内存中只保留当前块。

## 位置报错样例

输入 `/tmp/bad.md`：

~~~
1  # 标题
2
3  | a | b |
4  | --- | --- |
5  | 1 | 2 | 3 |
6
7  - 一层
8          - 过深
9
10 ```python
11 未闭合
~~~

运行 `python3 -m mdhtml /tmp/bad.md -o out.html`，stderr 输出：

```
/tmp/bad.md:5:6: 表格列数不一致：表头 2 列，本行 3 列
/tmp/bad.md:8:9: 非法嵌套：列表最多支持两层
/tmp/bad.md:10:1: 未闭合的代码围栏
```

进程正常退出（exit 0），同时产出 best-effort HTML。

## 大文档内存实测

环境：Python 3.12，输入 32.0 MiB 混合内容 Markdown（`bench/memory_bench.py` 生成）。

| 方式 | Python 堆峰值（tracemalloc） |
| --- | --- |
| 流式渲染 `render_lines`（文件->文件） | **0.08 MiB** |
| 一次性渲染 `render_markdown`（整串读入） | 258.68 MiB |

输出 HTML 54.4 MiB。流式路径内存与文档大小无关（只保留当前块），
几十兆输入可稳定在线处理；一次性路径峰值约为输入的 8 倍，
仅建议用于小文档。

## 目录

- `mdhtml/` 库源码（lexer / parser / inline / renderer / errors / CLI）
- `tests/test_render.py` 功能测试
- `tests/test_injection.py` 注入用例集（脚本标签、属性引号闭合、伪协议、注释伪造标记）
- `tests/test_errors.py` 位置报错样例
- `bench/memory_bench.py` 内存基准
