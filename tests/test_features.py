import unittest

from mdlite import render


def ok(md: str) -> str:
    html, errors = render(md)
    assert errors == [], f"unexpected errors: {errors}"
    return html


class TestBlocks(unittest.TestCase):
    def test_heading(self):
        self.assertEqual(ok("# Hello\n"), "<h1>Hello</h1>\n")
        self.assertEqual(ok("### Sub *em*\n"), "<h3>Sub <em>em</em></h3>\n")

    def test_paragraph(self):
        self.assertEqual(ok("hello\nworld\n"), "<p>hello\nworld</p>\n")

    def test_fence_code(self):
        html = ok("```python\nprint('<b>')\n```\n")
        self.assertEqual(
            html, "<pre><code>print('&lt;b&gt;')</code></pre>\n")

    def test_tilde_fence(self):
        self.assertEqual(ok("~~~\nx\n~~~\n"),
                         "<pre><code>x</code></pre>\n")

    def test_blockquote(self):
        self.assertEqual(ok("> quoted *text*\n"),
                         "<blockquote>\n<p>quoted <em>text</em></p>\n"
                         "</blockquote>\n")

    def test_table(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n"
        html = ok(md)
        self.assertIn("<th>a</th><th>b</th>", html)
        self.assertIn("<td>1</td><td>2</td>", html)

    def test_not_a_table_without_delim(self):
        html = ok("a | b\n")
        self.assertEqual(html, "<p>a | b</p>\n")


class TestLists(unittest.TestCase):
    def test_flat_list(self):
        html = ok("- a\n- b\n")
        self.assertEqual(html, "<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n")

    def test_ordered_list(self):
        html = ok("1. a\n2. b\n")
        self.assertEqual(html, "<ol>\n<li>a</li>\n<li>b</li>\n</ol>\n")

    def test_two_level_nesting(self):
        html = ok("- a\n  - a1\n  - a2\n- b\n")
        self.assertEqual(
            html,
            "<ul>\n<li>a\n<ul>\n<li>a1</li>\n<li>a2</li>\n</ul>\n</li>\n"
            "<li>b</li>\n</ul>\n")


class TestInline(unittest.TestCase):
    def test_em_strong_code(self):
        html = ok("*a* **b** `c`\n")
        self.assertEqual(
            html, "<p><em>a</em> <strong>b</strong> <code>c</code></p>\n")

    def test_nested_emphasis(self):
        html = ok("**a *b* c**\n")
        self.assertEqual(
            html, "<p><strong>a <em>b</em> c</strong></p>\n")

    def test_link(self):
        html = ok("[site](https://example.com)\n")
        self.assertEqual(
            html,
            '<p><a href="https://example.com" rel="nofollow noopener">'
            "site</a></p>\n")

    def test_relative_link(self):
        html = ok("[doc](/docs/a.md)\n")
        self.assertIn('href="/docs/a.md"', html)

    def test_unsupported_inline_left_alone(self):
        # ~~strike~~ and _em_ are not in the subset: pass through as text.
        html = ok("~~x~~ _y_\n")
        self.assertEqual(html, "<p>~~x~~ _y_</p>\n")

    def test_unmatched_marker_left_alone(self):
        html = ok("a * b\n")
        self.assertEqual(html, "<p>a * b</p>\n")


if __name__ == "__main__":
    unittest.main()
