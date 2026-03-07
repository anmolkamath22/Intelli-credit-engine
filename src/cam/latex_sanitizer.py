"""LaTeX escaping utilities."""

from __future__ import annotations

import re
import unicodedata


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
    # Replace common currency symbol with explicit unit text.
    s = s.replace("₹", "INR ")
    # Remove control chars and convert unsupported unicode into a safe ASCII subset.
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s).strip()
    out = []
    for ch in s:
        out.append(LATEX_ESCAPE_MAP.get(ch, ch))
    return "".join(out)
