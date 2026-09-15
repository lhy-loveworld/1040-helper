#!/usr/bin/env python3
"""Apply the simple state and local income tax refund recovery worksheet."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, NoReturn


MONEY = Decimal("0.01")
TOP_LEVEL_KEYS = {
    "tax_year",
    "refund_amount",
    "prior_income_tax_deduction",
    "total_salt_paid",
    "allowed_salt_deduction",
    "total_itemized_deductions",
    "applicable_standard_deduction",
    "eligibility",
}
ELIGIBILITY_KEYS = {
    "immediately_preceding_year",
    "itemized_deductions",
    "deducted_state_and_local_income_tax",
    "no_alternative_minimum_tax",
    "no_unused_tax_credits",
    "no_exception_cases",
    "same_filing_unit",
}
ESCALATION_GATES = ELIGIBILITY_KEYS - {
    "itemized_deductions",
    "deducted_state_and_local_income_tax",
}


class InputError(ValueError):
    """Raised when input does not match the calculator schema."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise InputError(message)


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise InputError(f"non-finite JSON number is not allowed: {value}")


def load_input(path: str) -> dict[str, Any]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read input file: {exc}") from exc
    try:
        value = json.loads(
            raw,
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicates,
        )
    except (json.JSONDecodeError, InputError) as exc:
        raise InputError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("input must be a JSON object")
    return value


def require_exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unknown:
            details.append(f"unknown {', '.join(unknown)}")
        raise InputError(f"{path}: {'; '.join(details)}")


def tax_year_field(value: Any) -> int:
    if isinstance(value, bool):
        raise InputError("tax_year must be a positive integer")
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise InputError("tax_year must be a positive integer")
        year = int(value)
    elif isinstance(value, int):
        year = value
    else:
        raise InputError("tax_year must be a positive integer")
    if year <= 0:
        raise InputError("tax_year must be a positive integer")
    return year


def decimal_field(value: Any, path: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, Decimal)):
        raise InputError(f"{path} must be a JSON number or decimal string")
    try:
        number = Decimal(value) if isinstance(value, str) else value
    except InvalidOperation as exc:
        raise InputError(f"{path} is not a valid decimal") from exc
    if not number.is_finite():
        raise InputError(f"{path} must be finite")
    if number < 0:
        raise InputError(f"{path} must be nonnegative")
    return number


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY, rounding=ROUND_HALF_UP), "f")


def zero_result(
    tax_year: int,
    refund: Decimal,
    reason: str,
) -> tuple[int, dict[str, Any]]:
    return 0, {
        "status": "ok",
        "tax_year": tax_year,
        "calculation": "state_and_local_income_tax_refund_worksheet_simple",
        "result": {
            "refund_amount": money(refund),
            "taxable_refund": "0.00",
        },
        "reason": reason,
        "warnings": [],
    }


def calculate(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    require_exact_keys(data, TOP_LEVEL_KEYS, "input")
    tax_year = tax_year_field(data["tax_year"])
    refund = decimal_field(data["refund_amount"], "refund_amount")
    prior_income_tax = decimal_field(
        data["prior_income_tax_deduction"], "prior_income_tax_deduction"
    )
    total_salt = decimal_field(data["total_salt_paid"], "total_salt_paid")
    allowed_salt = decimal_field(
        data["allowed_salt_deduction"], "allowed_salt_deduction"
    )
    itemized = decimal_field(
        data["total_itemized_deductions"], "total_itemized_deductions"
    )
    standard = decimal_field(
        data["applicable_standard_deduction"], "applicable_standard_deduction"
    )

    if prior_income_tax > total_salt:
        raise InputError("prior_income_tax_deduction cannot exceed total_salt_paid")
    if allowed_salt > total_salt:
        raise InputError("allowed_salt_deduction cannot exceed total_salt_paid")
    if allowed_salt > itemized:
        raise InputError(
            "allowed_salt_deduction cannot exceed total_itemized_deductions"
        )

    eligibility = data["eligibility"]
    if not isinstance(eligibility, dict):
        raise InputError("eligibility must be a JSON object")
    require_exact_keys(eligibility, ELIGIBILITY_KEYS, "eligibility")
    for gate in sorted(ELIGIBILITY_KEYS):
        if not isinstance(eligibility[gate], bool):
            raise InputError(f"eligibility.{gate} must be a JSON boolean")

    if not eligibility["itemized_deductions"]:
        return zero_result(
            tax_year,
            refund,
            "The taxpayer did not itemize deductions for the year of the payment.",
        )
    if not eligibility["deducted_state_and_local_income_tax"]:
        return zero_result(
            tax_year,
            refund,
            "State and local income tax was not deducted for the year of the payment.",
        )

    failed_gates = sorted(gate for gate in ESCALATION_GATES if not eligibility[gate])
    if failed_gates:
        return 3, {
            "status": "escalation",
            "tax_year": tax_year,
            "error": {
                "code": "unsupported_state_refund_case",
                "message": (
                    "The simple state and local income tax refund worksheet does not "
                    "cover this recovery. Use Publication 525 and the applicable "
                    "return-year instructions."
                ),
                "failed_gates": failed_gates,
            },
        }

    recovered_income_tax = min(refund, prior_income_tax)
    salt_after_refund = total_salt - recovered_income_tax
    redetermined_allowed_salt = min(allowed_salt, salt_after_refund)
    salt_deduction_reduction = max(
        Decimal(0), allowed_salt - redetermined_allowed_salt
    )
    itemization_tax_benefit = max(Decimal(0), itemized - standard)
    taxable_refund = min(
        recovered_income_tax,
        salt_deduction_reduction,
        itemization_tax_benefit,
    )

    return 0, {
        "status": "ok",
        "tax_year": tax_year,
        "calculation": "state_and_local_income_tax_refund_worksheet_simple",
        "result": {
            "refund_amount": money(refund),
            "refund_limited_to_prior_income_tax_deduction": money(
                recovered_income_tax
            ),
            "salt_paid_after_refund": money(salt_after_refund),
            "redetermined_allowed_salt_deduction": money(
                redetermined_allowed_salt
            ),
            "salt_deduction_reduction": money(salt_deduction_reduction),
            "itemized_deduction_tax_benefit_limit": money(
                itemization_tax_benefit
            ),
            "taxable_refund": money(taxable_refund),
        },
        "assumptions": sorted(ELIGIBILITY_KEYS),
        "warnings": [
            "This result applies only to the simple recovery case represented by the eligibility gates."
        ],
    }


def emit(payload: dict[str, Any], *, stream: Any) -> None:
    print(json.dumps(payload, sort_keys=True), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(
        description="Calculate a simple taxable state and local income tax refund.",
        epilog="Input schema: see ../references/calculator-inputs.md",
    )
    parser.add_argument("--input", required=True, help="Path to the calculator JSON input file")
    try:
        args = parser.parse_args(argv)
        exit_code, payload = calculate(load_input(args.input))
    except InputError as exc:
        emit(
            {
                "status": "error",
                "error": {"code": "invalid_input", "message": str(exc)},
            },
            stream=sys.stderr,
        )
        return 2

    emit(payload, stream=sys.stdout if exit_code == 0 else sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
