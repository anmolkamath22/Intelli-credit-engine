"""Table-first financial metric mapper from statement-like text blocks."""

from __future__ import annotations

import re
from typing import Any

CANONICAL_LABELS: dict[str, list[str]] = {
    "revenue": [
        "revenue from operations",
        "total income",
        "revenue",
        "income from operations",
    ],
    "ebitda": [
        "ebitda",
        "operating profit",
        "profit before interest tax depreciation amortisation",
    ],
    "net_profit": [
        "profit after tax",
        "net profit",
        "profit for the year",
        "profit for the period",
        "pat",
    ],
    "total_assets": [
        "total assets",
    ],
    "total_liabilities": [
        "total liabilities",
    ],
    "debt": [
        "borrowings",
        "total debt",
        "debt securities",
        "long term borrowings",
        "short term borrowings",
    ],
    "finance_cost": [
        "finance cost",
        "finance costs",
        "interest expense",
        "interest cost",
    ],
    "cash_flow": [
        "net cash from operating activities",
        "cash generated from operations",
        "net cash flow from operating activities",
        "cash flow from operating activities",
    ],
    "working_capital": [
        "working capital",
    ],
    "current_assets": [
        "total current assets",
        "current assets",
    ],
    "current_liabilities": [
        "total current liabilities",
        "current liabilities",
    ],
}

ANTI_PATTERNS = [
    "capex",
    "product launch",
    "governance",
    "tax footnote",
    "share capital",
    "director",
    "dividend",
]

PROSE_PATTERNS = [
    "compared", "increased", "decreased", "grew", "declined", "ended",
    "previous year", "for the year", "for the quarter", "is as follows", "refer note",
    "as at", "recovered", "basis", "excluding", "crore", "crores", "lakhs", "millions", "%"
]

def _extract_numbers(line: str) -> list[float]:
    nums = re.findall(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?", line)
    out: list[float] = []
    for n in nums:
        try:
            val = float(n.replace(",", ""))
            # Ignore clear dates like 31, or 2019-2025
            if val == 31.0 or val == 30.0 or val == 28.0 or val == 29.0:
                continue
            if 2015 <= val <= 2030:
                continue
            out.append(val)
        except Exception:
            continue
    return out


def _score_line_for_metric(line: str, aliases: list[str]) -> int:
    lo = line.lower()
    for anti in ANTI_PATTERNS:
        if anti in lo:
            return 0
            
    score = 0
    for a in aliases:
        if a in lo:
            score = max(score, len(a))
            
    # Substantial penalty for prose text
    for p in PROSE_PATTERNS:
        if p in lo:
            score -= 30
            
    return score


def extract_table_metrics_from_text(text: str) -> dict[str, Any]:
    """Extract current/previous-year metrics using statement row labels."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    current: dict[str, float] = {}
    previous: dict[str, float] = {}
    source_rows: dict[str, str] = {}
    confidence: dict[str, float] = {}

    for metric, aliases in CANONICAL_LABELS.items():
        best_line = ""
        best_score = -9999
        best_numbers: list[float] = []
        for ln in lines:
            s = _score_line_for_metric(ln, aliases)
            if s <= 0:
                continue
            nums = _extract_numbers(ln)
            if not nums:
                continue
            
            # Prefer table-like rows with >=2 numbers for year alignment.
            if len(nums) > 6:
                table_bonus = 0
            elif len(nums) >= 4:
                table_bonus = 100
            elif len(nums) >= 2:
                table_bonus = 60
            else:
                table_bonus = -20
                
            # Bonus if line is short (less like a paragraph)
            if len(ln) < 80:
                table_bonus += 20
            elif len(ln) > 150:
                table_bonus -= 40
                
            final_score = s + table_bonus
            if final_score > best_score:
                best_score = final_score
                best_line = ln
                best_numbers = nums
                
        if best_score > 0 and best_numbers:
            # Determine mapping logic based on standard tabular structures
            if len(best_numbers) >= 4:
                # Often table lines in these PDFs look like:
                # "Revenue from operations 9,685.36 7,977.32 8,998.88 7,353.13"
                # Usually Consolidated Current, Consolidated Prev, Standalone Curr, Standalone Prev
                current[metric] = best_numbers[0]
                previous[metric] = best_numbers[1]
            elif len(best_numbers) >= 2:
                current[metric] = best_numbers[0]
                previous[metric] = best_numbers[1]
            else:
                current[metric] = best_numbers[0]
                
            source_rows[metric] = best_line
            # Normalize confidence calculation to 100 scale for our new bonuses
            confidence[metric] = min(1.0, max(0.2, best_score / 150.0))

    return {
        "current": current,
        "previous": previous,
        "source_rows": source_rows,
        "confidence": confidence,
    }
