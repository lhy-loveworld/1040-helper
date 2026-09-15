"""End-to-end tests for the standalone calculator CLIs."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "1040-helper" / "scripts"

MORTGAGE_ELIGIBILITY = {
    "single_mortgage": True,
    "no_new_borrowing": True,
    "no_principal_prepayment_over_one_month": True,
    "level_payments": True,
    "qualified_home": True,
    "debt_used_to_buy_build_or_improve": True,
    "single_debt_category": True,
}

REFUND_ELIGIBILITY = {
    "immediately_preceding_year": True,
    "itemized_deductions": True,
    "deducted_state_and_local_income_tax": True,
    "no_alternative_minimum_tax": True,
    "no_unused_tax_credits": True,
    "no_exception_cases": True,
    "same_filing_unit": True,
}

PREFERENTIAL_ELIGIBILITY = {
    "schedule_d_tax_worksheet_not_required": True,
    "form_4952_adjustment_not_required": True,
    "no_28_percent_rate_gain": True,
    "no_unrecaptured_section_1250_gain": True,
    "form_2555_not_required": True,
    "form_8615_not_required": True,
}

FULL_BRACKETS = {
    "type": "brackets",
    "brackets": [
        {"up_to": "10000", "rate": "0.10"},
        {"up_to": "50000", "rate": "0.20"},
        {"up_to": None, "rate": "0.30"},
    ],
}


class CalculatorCliTests(unittest.TestCase):
    def run_calculator(
        self,
        script_name: str,
        payload: dict[str, Any] | None = None,
        *,
        raw: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            input_path.write_text(
                raw if raw is not None else json.dumps(payload),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / script_name),
                    "--input",
                    str(input_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:  # pragma: no cover - improves failures
            self.fail(
                f"{script_name} returned non-JSON output "
                f"(exit {completed.returncode}): {output!r}; stderr={completed.stderr!r}"
            )
            raise exc
        return completed, parsed

    def mortgage_input(self) -> dict[str, Any]:
        return {
            "tax_year": 2025,
            "beginning_principal": "810000",
            "ending_principal": "790000",
            "interest_paid": "40000",
            "qualified_loan_limit": "750000",
            "eligibility": dict(MORTGAGE_ELIGIBILITY),
        }

    def refund_input(self) -> dict[str, Any]:
        return {
            "tax_year": 2025,
            "refund_amount": "3000",
            "prior_income_tax_deduction": "7000",
            "total_salt_paid": "12000",
            "allowed_salt_deduction": "10000",
            "total_itemized_deductions": "20000",
            "applicable_standard_deduction": "15000",
            "eligibility": dict(REFUND_ELIGIBILITY),
        }

    def test_mortgage_rounds_ratio_before_applying_it(self) -> None:
        completed, output = self.run_calculator(
            "calc_mortgage.py", self.mortgage_input()
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["tax_year"], 2025)
        self.assertEqual(output["result"]["average_mortgage_balance"], "800000.00")
        self.assertEqual(output["result"]["deductible_ratio"], "0.938")
        self.assertEqual(
            output["result"]["deductible_mortgage_interest"], "37520.00"
        )

    def test_mortgage_below_limit_allows_all_interest(self) -> None:
        payload = self.mortgage_input()
        payload["beginning_principal"] = "700000"
        payload["ending_principal"] = "680000"
        completed, output = self.run_calculator("calc_mortgage.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["result"]["deductible_ratio"], "1.000")
        self.assertEqual(
            output["result"]["deductible_mortgage_interest"], "40000.00"
        )

    def test_mortgage_failed_gate_escalates(self) -> None:
        payload = self.mortgage_input()
        payload["eligibility"]["no_new_borrowing"] = False
        completed, output = self.run_calculator("calc_mortgage.py", payload)
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(output["status"], "escalation")
        self.assertIn("no_new_borrowing", output["error"]["failed_gates"])
        self.assertEqual(completed.stdout, "")

    def test_state_refund_applies_salt_and_itemization_limits(self) -> None:
        completed, output = self.run_calculator(
            "calc_state_refund.py", self.refund_input()
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["tax_year"], 2025)
        self.assertEqual(output["result"]["salt_deduction_reduction"], "1000.00")
        self.assertEqual(output["result"]["taxable_refund"], "1000.00")

    def test_state_refund_that_remains_above_salt_cap_is_zero(self) -> None:
        payload = self.refund_input()
        payload["refund_amount"] = "2000"
        payload["total_salt_paid"] = "15000"
        completed, output = self.run_calculator("calc_state_refund.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["result"]["taxable_refund"], "0.00")

    def test_state_refund_is_zero_when_taxpayer_did_not_itemize(self) -> None:
        payload = self.refund_input()
        payload["eligibility"]["itemized_deductions"] = False
        completed, output = self.run_calculator("calc_state_refund.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["result"]["taxable_refund"], "0.00")
        self.assertIn("did not itemize", output["reason"])

    def test_state_refund_exception_gate_escalates(self) -> None:
        payload = self.refund_input()
        payload["eligibility"]["no_alternative_minimum_tax"] = False
        completed, output = self.run_calculator("calc_state_refund.py", payload)
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(output["status"], "escalation")
        self.assertIn(
            "no_alternative_minimum_tax", output["error"]["failed_gates"]
        )

    def test_ordinary_tax_uses_complete_brackets(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "ordinary",
            "taxable_income": "60000",
            "ordinary_tax": FULL_BRACKETS,
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["tax_year"], 2025)
        self.assertEqual(
            output["result"]["income_tax_before_credits_and_additional_taxes"],
            "12000.00",
        )
        self.assertNotIn("total_federal_tax", output["result"])

    def test_ordinary_tax_accepts_a_supplied_tax_table(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "ordinary",
            "taxable_income": "15000",
            "ordinary_tax": {
                "type": "table",
                "rows": [
                    {"at_least": "0", "less_than": "10000", "tax": "500"},
                    {"at_least": "10000", "less_than": "20000", "tax": "1500"},
                ],
            },
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["ordinary_tax_source"], "table")
        self.assertEqual(
            output["result"]["income_tax_before_credits_and_additional_taxes"],
            "1500.00",
        )

    def test_tax_table_may_contain_only_the_relevant_sparse_rows(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "ordinary",
            "taxable_income": "45025",
            "ordinary_tax": {
                "type": "table",
                "rows": [
                    {"at_least": "10000", "less_than": "10050", "tax": "1000"},
                    {"at_least": "45000", "less_than": "45050", "tax": "5200"},
                ],
            },
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            output["result"]["income_tax_before_credits_and_additional_taxes"],
            "5200.00",
        )

    def test_qualified_dividend_mode_accepts_exact_irs_tax_values(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "qualified_dividends_capital_gain",
            "taxable_income": "100000",
            "qualified_dividends": "10000",
            "worksheet_line_3_capital_gain": "10000",
            "zero_rate_threshold": "50000",
            "fifteen_rate_threshold": "90000",
            "ordinary_tax": {
                "type": "values",
                "values": [
                    {"income": "80000", "tax": "15000"},
                    {"income": "100000", "tax": "23000"},
                ],
            },
            "eligibility": dict(PREFERENTIAL_ELIGIBILITY),
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["ordinary_tax_source"], "values")
        self.assertEqual(
            output["result"]["income_tax_before_credits_and_additional_taxes"],
            "18500.00",
        )

    def test_exact_tax_values_must_cover_every_requested_income(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "qualified_dividends_capital_gain",
            "taxable_income": "100000",
            "qualified_dividends": "10000",
            "worksheet_line_3_capital_gain": "10000",
            "zero_rate_threshold": "50000",
            "fifteen_rate_threshold": "90000",
            "ordinary_tax": {
                "type": "values",
                "values": [{"income": "80000", "tax": "15000"}],
            },
            "eligibility": dict(PREFERENTIAL_ELIGIBILITY),
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("do not include taxable income 100000", output["error"]["message"])

    def test_incomplete_brackets_are_rejected(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "ordinary",
            "taxable_income": "150",
            "ordinary_tax": {
                "type": "brackets",
                "brackets": [{"up_to": "100", "rate": "0.10"}],
            },
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(output["status"], "error")
        self.assertIn("do not cover", output["error"]["message"])

    def test_qualified_dividend_capital_gain_worksheet(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "qualified_dividends_capital_gain",
            "taxable_income": "100000",
            "qualified_dividends": "10000",
            "worksheet_line_3_capital_gain": "10000",
            "zero_rate_threshold": "50000",
            "fifteen_rate_threshold": "90000",
            "ordinary_tax": FULL_BRACKETS,
            "eligibility": dict(PREFERENTIAL_ELIGIBILITY),
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        result = output["result"]
        self.assertEqual(result["ordinary_taxable_income"], "80000.00")
        self.assertEqual(result["zero_percent_amount"], "0.00")
        self.assertEqual(result["fifteen_percent_amount"], "10000.00")
        self.assertEqual(result["twenty_percent_amount"], "10000.00")
        self.assertEqual(
            result["income_tax_before_credits_and_additional_taxes"], "21500.00"
        )

    def test_qualified_dividend_alternate_worksheet_gate_escalates(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "qualified_dividends_capital_gain",
            "taxable_income": "100000",
            "qualified_dividends": "10000",
            "worksheet_line_3_capital_gain": "10000",
            "zero_rate_threshold": "50000",
            "fifteen_rate_threshold": "90000",
            "ordinary_tax": FULL_BRACKETS,
            "eligibility": dict(PREFERENTIAL_ELIGIBILITY),
        }
        payload["eligibility"]["no_unrecaptured_section_1250_gain"] = False
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(output["status"], "escalation")
        self.assertIn(
            "no_unrecaptured_section_1250_gain",
            output["error"]["failed_gates"],
        )

    def test_preferential_income_is_limited_to_taxable_income(self) -> None:
        payload = {
            "tax_year": 2025,
            "mode": "qualified_dividends_capital_gain",
            "taxable_income": "5000",
            "qualified_dividends": "7000",
            "worksheet_line_3_capital_gain": "0",
            "zero_rate_threshold": "50000",
            "fifteen_rate_threshold": "90000",
            "ordinary_tax": FULL_BRACKETS,
            "eligibility": dict(PREFERENTIAL_ELIGIBILITY),
        }
        completed, output = self.run_calculator("calc_tax.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(output["result"]["ordinary_taxable_income"], "0.00")
        self.assertEqual(output["result"]["preferential_income"], "5000.00")
        self.assertEqual(
            output["result"]["reported_qualified_dividends_and_line_3_capital_gain"],
            "7000.00",
        )
        self.assertEqual(
            output["result"]["income_tax_before_credits_and_additional_taxes"],
            "0.00",
        )

    def test_negative_inputs_fail_for_every_calculator(self) -> None:
        mortgage = self.mortgage_input()
        mortgage["interest_paid"] = "-0.01"
        refund = self.refund_input()
        refund["refund_amount"] = "-0.01"
        tax = {
            "tax_year": 2025,
            "mode": "ordinary",
            "taxable_income": "-0.01",
            "ordinary_tax": FULL_BRACKETS,
        }
        for script, payload in (
            ("calc_mortgage.py", mortgage),
            ("calc_state_refund.py", refund),
            ("calc_tax.py", tax),
        ):
            with self.subTest(script=script):
                completed, output = self.run_calculator(script, payload)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(output["status"], "error")
                self.assertIn("nonnegative", output["error"]["message"])

    def test_malformed_json_fails_with_structured_error(self) -> None:
        for script in (
            "calc_mortgage.py",
            "calc_state_refund.py",
            "calc_tax.py",
        ):
            with self.subTest(script=script):
                completed, output = self.run_calculator(
                    script, raw='{"tax_year": 2025,'
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(output["status"], "error")
                self.assertEqual(output["error"]["code"], "invalid_input")
                self.assertEqual(completed.stdout, "")

    def test_unknown_fields_and_invalid_tax_year_are_rejected(self) -> None:
        payload = self.mortgage_input()
        payload["unexpected"] = True
        completed, output = self.run_calculator("calc_mortgage.py", payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("unknown unexpected", output["error"]["message"])

        payload = self.refund_input()
        payload["tax_year"] = 0
        completed, output = self.run_calculator("calc_state_refund.py", payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("positive integer", output["error"]["message"])


if __name__ == "__main__":
    unittest.main()
