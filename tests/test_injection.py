"""注入用例集：脚本标签、属性闭合、伪协议、注释伪造标记，均不得穿透。"""

import re
import unittest

from mdhtml import render_markdown


def render(text):
    return render_markdown(text).html


class TestInjection(unittest.TestCase):
    def assert_no_raw(self, html, *needles):
        for needle in needles:
            self.assertNotIn(needle, html, f"未转义的危险片段穿透: {needle!r}")

    def test_script_tag_in_paragraph(self):
        html = render("<script>alert(1)</script>\n")
        self.assert_no_raw(html, "<script>")
        self.assertIn("&lt;script&gt;", html)

    def test_script_tag_in_heading_and_list(self):
        html = render("# <script>alert(1)</script>\n- <img src=x onerror=alert(1)>\n")
        self.assert_no_raw(html, "<script>", "<img ")

    def test_script_inside_code_span_and_fence(self):
        html = render("`<script>alert(1)</script>`\n\n```\n</code></pre><script>alert(1)</script>\n```\n")
        self.assert_no_raw(html, "<script>")
        self.assertIn("&lt;/code&gt;&lt;/pre&gt;", html)

    def test_attribute_quote_breakout_in_link(self):
        # 试图用引号闭合 href 并注入事件属性（无空格，确保进入链接分支）
        html = render('[点我](https://a.com/"onmouseover="alert(1))\n')
        self.assert_no_raw(html, 'onclick="alert')
        self.assert_no_raw(html, 'onmouseover="alert')
        self.assertIn("&quot;", html)
        # href 属性值内不允许出现未转义的引号
        m = re.search(r'href="([^"]*)"', html)
        self.assertIsNotNone(m)
        self.assertNotIn('"', m.group(1))

    def test_url_with_space_rejected(self):
        # 含空格的 URL 不合法，整体按普通文本输出，不产生链接
        html = render('[点我](https://a.com/" onclick="alert(1))\n')
        self.assertNotIn("<a ", html)

    def test_html_attribute_in_plain_text(self):
        html = render('"><img src=x onerror=alert(1)>\n')
        self.assert_no_raw(html, "<img ")

    def test_javascript_pseudo_protocol(self):
        for url in ("javascript:alert(1)",
                    "JaVaScRiPt:alert(1)",
                    "javascript:alert(1)"):
            html = render(f"[x]({url})\n")
            self.assertNotIn("href", html)

    def test_javascript_with_embedded_tab(self):
        html = render("[x](java\tscript:alert(1))\n")
        self.assertNotIn("javascript", html)

    def test_data_and_vbscript_protocol(self):
        html = render("[x](data:text/html,<script>alert(1)</script>)\n")
        self.assertNotIn("href", html)
        html = render("[x](vbscript:msgbox)\n")
        self.assertNotIn("href", html)

    def test_protocol_relative_url_rejected(self):
        html = render("[x](//evil.example/x)\n")
        self.assertNotIn("href", html)

    def test_allowed_protocols_kept(self):
        for url in ("https://a.com", "http://a.com", "mailto:a@b.c",
                    "/relative/path", "page.md", "#anchor"):
            html = render(f"[x]({url})\n")
            self.assertIn(f'href="{url}"', html)

    def test_comment_forged_markup(self):
        # 注释内伪造的闭合标记不得穿透
        html = render("<!-- </p><script>alert(1)</script> -->\n")
        self.assert_no_raw(html, "<script>", "<!--", "-->")
        self.assertIn("&lt;!--", html)

    def test_comment_hides_fake_table_and_fence(self):
        html = render("<!-- ``` -->\n\n<!-- | a | b | -->\n")
        self.assert_no_raw(html, "<!--", "-->")
        self.assertNotIn("<pre>", html)
        self.assertNotIn("<table>", html)

    def test_table_cell_injection(self):
        html = render("| a |\n| --- |\n| <script>alert(1)</script> |\n")
        self.assert_no_raw(html, "<script>")

    def test_link_label_injection(self):
        html = render("[<script>alert(1)</script>](https://a.com)\n")
        self.assert_no_raw(html, "<script>")

    def test_no_uncaught_exception_on_garbage(self):
        garbage = "\x00\x01<a '`'*[](|>###```\n```\n" * 50
        html = render(garbage)  # 不应抛任何异常
        self.assertIsInstance(html, str)


if __name__ == "__main__":
    unittest.main()
