"""Tests for CAM payload schema validation."""

from __future__ import annotations

import unittest

from src.cam.cam_json_schema import validate_cam_payload


def _valid_payload() -> dict:
    return {
        "title": "Credit Appraisal Memo",
        "company_name": "Blue Star Ltd",
        "reporting_note": "All financial values are reported in INR Crores unless otherwise stated.",
        "executive_summary": "Summary",
        "company_overview": "Overview",
        "financial_performance": {
            "narrative": "Financial narrative",
            "table": {"headers": ["Metric", "FY24"], "rows": [["Revenue", "100.00"]]},
        },
        "promoter_analysis": "Promoter analysis",
        "industry_outlook": "Industry outlook",
        "litigation_profile": "Litigation profile",
        "risk_flags": [{"flag": "High leverage", "explanation": "Debt elevated"}],
        "decision_logic": "Decision logic",
        "final_credit_score": "75.20 / 100",
        "recommended_loan_limit_crore": "45.00",
        "interest_rate_percent": "11.25",
        "supporting_evidence": [{"source": "annual_reports", "excerpt": "sample"}],
    }


class CamJsonSchemaTests(unittest.TestCase):
    def test_valid_payload(self) -> None:
        ok, errors = validate_cam_payload(_valid_payload())
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_missing_required_field(self) -> None:
        p = _valid_payload()
        p.pop("executive_summary")
        ok, errors = validate_cam_payload(p)
        self.assertFalse(ok)
        self.assertTrue(any("executive_summary" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

