"""Fixed LaTeX template for CAM rendering."""

from __future__ import annotations


def get_latex_template() -> str:
    """Return compile-safe LaTeX template with placeholders."""
    return r"""
\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{lmodern}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\setlength{\parskip}{0.6em}
\setlength{\parindent}{0pt}

\begin{document}

\begin{center}
    {\LARGE \textbf{{{TITLE}}}}\\[0.4em]
    {\large {COMPANY\_NAME}}\\[0.2em]
\end{center}

\vspace{0.3em}
\colorbox{gray!12}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{\textbf{Reporting Note:} {REPORTING\_NOTE}}}
\vspace{0.6em}

{CONTENT}

\end{document}
"""
