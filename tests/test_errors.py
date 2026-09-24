"""位置报错样例：未闭合围栏、表格列数不一致、非法嵌套。"""

import unittest

from mdhtml import render_markdown


class TestErrorPositions(unittest.TestCase):
    def test_unclosed_fence_reports_open_position(self):
        result = render_markdown("# t\n\n```python\ncode\n")
        self.assertEqual(len(result.errors), 1)
        err = result.errors[0]
        self.assertEqual((err.line, err.col), (3, 1))
        self.assertIn("未闭合", err.message)
        # 仍然给出 best-effort 输出，不抛异常
        self.assertIn("<pre><code", result.html)

    def test_indented_unclosed_fence_col(self):
        result = render_markdown("x\n\n  ```\ny\n")
        self.assertEqual((result.errors[0].line, result.errors[0].col), (3, 3))

    def test_table_column_mismatch(self):
        md = "| a | b |\n| --- | --- |\n| 1 | 2 | 3 |\n| 4 |\n"
        result = render_markdown(md)
        self.assertEqual(len(result.errors), 2)
        first, second = result.errors
        self.assertEqual(first.line, 3)
        self.assertIn("表头 2 列，本行 3 列", first.message)
        self.assertEqual(second.line, 4)
        self.assertIn("表头 2 列，本行 1 列", second.message)
        # 表格仍被渲染（单元格截断/补齐）
        self.assertIn("<table>", result.html)

    def test_illegal_list_nesting(self):
        md = "- 一层\n    - 两层\n        - 三层\n"
        result = render_markdown(md)
        self.assertEqual(len(result.errors), 1)
        err = result.errors[0]
        self.assertEqual(err.line, 3)
        self.assertEqual(err.col, 9)
        self.assertIn("非法嵌套", err.message)
        # 超深内容降级为文本保留，不丢失
        self.assertIn("三层", result.html)

    def test_errors_do_not_raise(self):
        md = ("| a |\n| - |\n| 1 | 2 |\n\n        - 过深\n\n```\n未闭合\n")
        result = render_markdown(md)
        self.assertGreaterEqual(len(result.errors), 3)
        self.assertIsInstance(result.html, str)

    def test_error_str_format(self):
        result = render_markdown("```\n")
        self.assertRegex(str(result.errors[0]), r"line 1, col 1: ")


if __name__ == "__main__":
    unittest.main()
