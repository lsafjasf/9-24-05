"""基础渲染功能测试。"""

import unittest

from mdhtml import render_markdown


def render(text):
    result = render_markdown(text)
    return result.html, result.errors


class TestBlocks(unittest.TestCase):
    def test_heading(self):
        html, errors = render("# 标题\n## 二级\n")
        self.assertIn("<h1>标题</h1>", html)
        self.assertIn("<h2>二级</h2>", html)
        self.assertEqual(errors, [])

    def test_paragraph(self):
        html, _ = render("第一段\n换行\n\n第二段\n")
        self.assertIn("<p>第一段\n换行</p>", html)
        self.assertIn("<p>第二段</p>", html)

    def test_fence_code(self):
        html, errors = render("```python\nprint(1 < 2)\n```\n")
        self.assertIn('<pre><code class="language-python">print(1 &lt; 2)</code></pre>', html)
        self.assertEqual(errors, [])

    def test_quote(self):
        html, _ = render("> 引用 *内容*\n")
        self.assertIn("<blockquote>", html)
        self.assertIn("<em>内容</em>", html)

    def test_two_level_list(self):
        html, errors = render("- 甲\n    - 甲一\n    - 甲二\n- 乙\n")
        self.assertEqual(errors, [])
        self.assertEqual(html.count("<ul>"), 2)
        self.assertIn("<li>甲一</li>", html)

    def test_ordered_list(self):
        html, _ = render("1. 一\n2. 二\n")
        self.assertIn("<ol>", html)

    def test_table(self):
        html, errors = render("| 名 | 值 |\n| --- | --- |\n| a | 1 |\n")
        self.assertEqual(errors, [])
        self.assertIn("<th>名</th>", html)
        self.assertIn("<td>a</td>", html)


class TestInlines(unittest.TestCase):
    def test_emphasis_and_strong(self):
        html, _ = render("*斜体* 与 **粗体**\n")
        self.assertIn("<em>斜体</em>", html)
        self.assertIn("<strong>粗体</strong>", html)

    def test_inline_code(self):
        html, _ = render("使用 `x < y` 比较\n")
        self.assertIn("<code>x &lt; y</code>", html)

    def test_link(self):
        html, _ = render("[站点](https://example.com)\n")
        self.assertIn('<a href="https://example.com">站点</a>', html)

    def test_unclosed_marks_stay_literal(self):
        html, _ = render("未闭合 *星号 和 `反引号\n")
        self.assertIn("*星号", html)
        self.assertIn("`反引号", html)

    def test_unsupported_syntax_passthrough(self):
        # 删除线、图片、七级标题等不支持的语法按普通文本原样输出
        html, _ = render("~~删除~~ ![图](x.png)\n####### 七级\n")
        self.assertIn("~~删除~~", html)
        self.assertIn("![图](x.png)", html)
        self.assertIn("####### 七级", html)


if __name__ == "__main__":
    unittest.main()
