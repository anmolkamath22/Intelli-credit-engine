"""LaTeX escaping utilities."""

from __future__ import annotations


LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: object) -> str:
    """Escape LaTeX special characters in arbitrary text input."""
    s = str(text if text is not None else "")
    out = []
    for ch in s:
        out.append(LATEX_ESCAPE_MAP.get(ch, ch))
    return "".join(out)

