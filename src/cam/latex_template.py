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
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue!50!black}
\setlength{\arrayrulewidth}{0.4pt}
\renewcommand{\arraystretch}{1.15}
\setlength{\parskip}{0.6em}
\setlength{\parindent}{0pt}

\begin{document}

\begin{center}
    {\LARGE \textbf{\textcolor{blue!50!black}{{TITLE}}}}\\[0.5em]
    {\large \textbf{{COMPANY\_NAME}}}\\[0.2em]
    {\small Credit Underwriting Assessment}
\end{center}
\vspace{0.4em}
\noindent\textcolor{blue!50!black}{\rule{\linewidth}{0.6pt}}

\vspace{0.3em}
\colorbox{blue!5}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{\textbf{Reporting Note:} {REPORTING\_NOTE}}}
\vspace{0.6em}

{CONTENT}

\end{document}
"""
