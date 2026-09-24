"""Injection test suite: script tags, attribute breakout, pseudo-protocol
links and fake markup inside comments must never reach the output raw.
"""
import re
import unittest

from mdlite import render


def out(md: str) -> str:
    html, _ = render(md)
    return html


class TestScriptInjection(unittest.TestCase):
    def test_script_tag_in_paragraph(self):
        html = out("<script>alert(1)</script>\n")
        self.assertNotIn("<script", html)
        self.assertIn("&lt;script&gt;", html)

    def test_script_tag_in_inline_code(self):
        html = out("`<script>alert(1)</script>`\n")
        self.assertNotIn("<script", html)

    def test_script_tag_in_fence(self):
        html = out("```\n<script>alert(1)</script>\n```\n")
        self.assertNotIn("<script", html)

    def test_script_tag_in_heading_and_table(self):
        html = out("# <script>x</script>\n\n| <script>y</script> |\n|---|\n")
        self.assertNotIn("<script", html)

    def test_event_handler_attribute(self):
        html = out("<img src=x onerror=alert(1)>\n")
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)


class TestAttributeBreakout(unittest.TestCase):
    def test_quote_in_url_is_escaped(self):
        html = out('[x]("onmouseover="alert(1))\n')
        m = re.search(r'href="([^"]*)"', html)
        self.assertIsNotNone(m)
        self.assertNotIn('"', m.group(1))
        self.assertNotIn('onmouseover="', html)

    def test_quote_in_link_text(self):
        html = out('[" onclick="x](https://example.com)\n')
        # The quote may appear as inert text content, but the <a> tag
        # itself must not gain an onclick attribute.
        tag = re.search(r"<a [^>]*>", html)
        self.assertIsNotNone(tag)
        self.assertNotIn("onclick", tag.group(0))


class TestPseudoProtocol(unittest.TestCase):
    def test_javascript_scheme(self):
        html = out("[x](javascript:alert(1))\n")
        self.assertNotIn("javascript:", html)
        self.assertNotIn("<a ", html)

    def test_javascript_mixed_case(self):
        html = out("[x](JaVaScRiPt:alert(1))\n")
        self.assertNotIn("<a ", html)

    def test_javascript_with_control_chars(self):
        html = out("[x](java\tscript:alert(1))\n")
        self.assertNotIn("<a ", html)

    def test_data_and_vbscript(self):
        for url in ("data:text/html,<script>alert(1)</script>",
                    "vbscript:msgbox(1)"):
            html = out(f"[x]({url})\n")
            self.assertNotIn("<a ", html, url)

    def test_protocol_relative_blocked(self):
        html = out("[x](//evil.example/x)\n")
        self.assertNotIn("<a ", html)

    def test_entity_encoded_colon_neutralised(self):
        # & is escaped, so the browser never sees a javascript: scheme.
        html = out("[x](javascript&colon;alert(1))\n")
        self.assertNotIn("javascript&colon;", html)
        self.assertNotIn("javascript:", html)


class TestCommentFakeMarkup(unittest.TestCase):
    def test_comment_with_script(self):
        html = out("<!-- <script>alert(1)</script> -->\n")
        self.assertNotIn("<!--", html)
        self.assertNotIn("<script", html)

    def test_comment_closing_fake_tag(self):
        html = out("--><script>alert(1)</script>\n")
        self.assertNotIn("<script", html)

    def test_conditional_comment(self):
        html = out("<!--[if IE]><script>alert(1)</script><![endif]-->\n")
        self.assertNotIn("<script", html)


class TestNoRawHtmlAnywhere(unittest.TestCase):
    def test_output_contains_no_raw_angle_brackets_from_input(self):
        md = ("# <b>x</b>\n\n<div onclick='x'>t</div>\n\n"
              "| <i>y</i> |\n|---|\n\n> <u>z</u>\n")
        html = out(md)
        for tag in ("<b>", "<div", "<i>", "<u>"):
            self.assertNotIn(tag, html)


if __name__ == "__main__":
    unittest.main()
