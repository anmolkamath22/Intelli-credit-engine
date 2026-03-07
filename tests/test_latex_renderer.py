"""Tests for deterministic LaTeX rendering."""

from __future__ import annotations

import unittest

from src.cam.latex_renderer import render_cam_payload_to_latex


class LatexRendererTests(unittest.TestCase):
    def test_renders_table_and_sections(self) -> None:
        payload = {
            "title": "Credit Appraisal Memo",
            "company_name": "Demo Co",
            "reporting_note": "All financial values are reported in INR Crores unless otherwise stated.",
            "executive_summary": "Summary text",
            "company_overview": "Overview text",
            "financial_performance": {
                "narrative": "Narrative",
                "table": {
                    "headers": ["Metric", "FY24"],
                    "rows": [["Revenue", "100.00"], ["EBITDA", "15.00"]],
                },
            },
            "promoter_analysis": "Promoter analysis",
            "industry_outlook": "Industry outlook",
            "litigation_profile": "Litigation profile",
            "risk_flags": [{"flag": "High leverage", "explanation": "Debt is high"}],
            "decision_logic": "Decision logic",
            "final_credit_score": "72.10 / 100",
            "recommended_loan_limit_crore": "20.00",
            "interest_rate_percent": "11.00",
            "supporting_evidence": [{"source": "annual_reports", "excerpt": "evidence"}],
        }
        latex = render_cam_payload_to_latex(payload)
        self.assertIn(r"\section*{Executive Summary}", latex)
        self.assertIn(r"\begin{longtable}", latex)
        self.assertIn("Revenue", latex)
        self.assertIn(r"\section*{Supporting Evidence}", latex)


if __name__ == "__main__":
    unittest.main()

