"""Parse errors must carry line/col positions and must never raise."""
import unittest

from mdlite import render


class TestErrorPositions(unittest.TestCase):
    def test_unclosed_fence_reports_open_line(self):
        md = "intro\n\n```python\ncode line\nmore\n"
        html, errors = render(md)
        self.assertEqual(len(errors), 1)
        err = errors[0]
        self.assertEqual((err.line, err.col), (3, 1))
        self.assertIn("未闭合", err.message)
        self.assertIn("<pre><code>", html)

    def test_table_column_mismatch_reports_bad_row(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 | 5 |\n"
        html, errors = render(md)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line, 4)
        self.assertIn("列数不一致", errors[0].message)
        self.assertIn("<table>", html)

    def test_table_multi_extra_cells_points_at_first_extra(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 | 3 | 4 |\n"
        html, errors = render(md)
        self.assertEqual(len(errors), 1)
        err = errors[0]
        self.assertEqual(err.line, 3)
        # "| 1 | 2 | 3 | 4 |": first extra cell "3" starts at column 11
        self.assertEqual(err.col, 11)
        self.assertIn("第 3 列", err.message)
        self.assertIn("3", err.message)
        self.assertIn("<table>", html)

    def test_table_missing_cell_points_at_gap(self):
        md = "| a | b | c |\n|---|---|---|\n| 1 | 2 |\n"
        _, errors = render(md)
        self.assertEqual(len(errors), 1)
        err = errors[0]
        self.assertEqual(err.line, 3)
        # "| 1 | 2 |": missing 3rd cell would sit at the closing "|" (col 9)
        self.assertEqual(err.col, 9)
        self.assertIn("缺少第 3 列", err.message)

    def test_illegal_list_nesting_reports_position(self):
        md = "- a\n  - b\n    - c\n"
        html, errors = render(md)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line, 3)
        self.assertEqual(errors[0].col, 5)
        self.assertIn("非法嵌套", errors[0].message)
        self.assertIn("<ul>", html)

    def test_multiple_errors_all_reported(self):
        md = "| a |\n|---|\n| 1 | 2 |\n\n```\nx\n"
        _, errors = render(md)
        self.assertEqual(len(errors), 2)
        self.assertEqual([e.line for e in errors], [3, 5])

    def test_no_uncaught_exceptions_on_garbage(self):
        garbage = ("```\n" + "| a |\n" * 3 + "- x\n    - y\n      - z\n"
                   "[](()) ** `` ` * [ |\x00\x01\n")
        html, errors = render(garbage)  # must not raise
        self.assertIsInstance(html, str)
        self.assertTrue(errors)

    def test_str_format(self):
        _, errors = render("```\n")
        self.assertRegex(str(errors[0]), r"^1:1: ")


if __name__ == "__main__":
    unittest.main()
