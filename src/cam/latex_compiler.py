"""Local LaTeX compilation helper."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def detect_latex_compiler() -> str | None:
    """Detect available LaTeX compiler with preferred order."""
    for cmd in ["tectonic", "xelatex", "pdflatex"]:
        if shutil.which(cmd):
            return cmd
    return None


def _compiler_command(compiler: str, tex_path: Path) -> list[str]:
    if compiler == "tectonic":
        return ["tectonic", "--keep-logs", "--outdir", str(tex_path.parent), str(tex_path)]
    return [compiler, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]


def compile_latex(tex_path: Path, log_path: Path) -> dict:
    """Compile .tex to PDF using best available local compiler."""
    tex_path = tex_path.resolve()
    log_path = log_path.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    compiler = detect_latex_compiler()
    if not compiler:
        msg = "No LaTeX compiler found. Install tectonic, xelatex, or pdflatex."
        log_path.write_text(msg + "\n", encoding="utf-8")
        return {
            "success": False,
            "compiler": None,
            "pdf_path": str(tex_path.with_suffix(".pdf")),
            "log_path": str(log_path),
            "error": msg,
        }

    cmd = _compiler_command(compiler, tex_path)
    result = subprocess.run(
        cmd,
        cwd=str(tex_path.parent),
        capture_output=True,
        text=True,
        check=False,
    )

    log_text = f"$ {' '.join(cmd)}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
    log_path.write_text(log_text, encoding="utf-8")

    pdf_path = tex_path.with_suffix(".pdf")
    ok = result.returncode == 0 and pdf_path.exists()
    return {
        "success": bool(ok),
        "compiler": compiler,
        "pdf_path": str(pdf_path),
        "log_path": str(log_path),
        "error": None if ok else f"Compilation failed with {compiler} (code={result.returncode})",
    }

