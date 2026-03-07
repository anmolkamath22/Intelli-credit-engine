"""Tests for LaTeX compiler selection."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.cam.latex_compiler import detect_latex_compiler


class LatexCompilerTests(unittest.TestCase):
    @patch("shutil.which")
    def test_detect_prefers_tectonic(self, which_mock) -> None:  # type: ignore[no-untyped-def]
        which_mock.side_effect = lambda x: "/usr/bin/" + x if x in {"tectonic", "xelatex", "pdflatex"} else None
        self.assertEqual(detect_latex_compiler(), "tectonic")

    @patch("shutil.which")
    def test_detect_xelatex_when_tectonic_missing(self, which_mock) -> None:  # type: ignore[no-untyped-def]
        def _fake(cmd: str) -> str | None:
            if cmd == "tectonic":
                return None
            if cmd == "xelatex":
                return "/usr/bin/xelatex"
            return None

        which_mock.side_effect = _fake
        self.assertEqual(detect_latex_compiler(), "xelatex")


if __name__ == "__main__":
    unittest.main()

