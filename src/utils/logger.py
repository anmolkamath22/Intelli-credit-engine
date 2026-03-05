"""Logging setup for intelli-credit-engine."""

from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str = "intelli_credit_engine", log_file: str | None = None) -> logging.Logger:
    """Return configured logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
