"""Tests for LaTeX escaping."""

from __future__ import annotations

import unittest

from src.cam.latex_sanitizer import escape_latex


class LatexSanitizerTests(unittest.TestCase):
    def test_escape_all_special_chars(self) -> None:
        text = r"# $ % & ~ _ ^ \ { }"
        escaped = escape_latex(text)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\textasciitilde{}", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\textasciicircum{}", escaped)
        self.assertIn(r"\textbackslash{}", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)


if __name__ == "__main__":
    unittest.main()

