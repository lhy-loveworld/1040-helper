#!/usr/bin/env python3
"""Calculate deductible interest for one simple acquisition-debt mortgage.

Only the Publication 936 average-of-first-and-last-balance shortcut is
implemented. If any prerequisite is false, the calculator fails closed with a
structured escalation rather than returning an estimate.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, NoReturn


MONEY = Decimal("0.01")
RATIO = Decimal("0.001")
TOP_LEVEL_KEYS = {
    "tax_year",
    "beginning_principal",
    "ending_principal",
    "interest_paid",
    "qualified_loan_limit",
    "eligibility",
}
ELIGIBILITY_KEYS = {
    "single_mortgage",
    "no_new_borrowing",
    "no_principal_prepayment_over_one_month",
    "level_payments",
    "qualified_home",
    "debt_used_to_buy_build_or_improve",
    "single_debt_category",
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


def decimal_field(value: Any, path: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, Decimal)):
        raise InputError(f"{path} must be a JSON number or decimal string")
    try:
        number = Decimal(value) if isinstance(value, str) else value
    except InvalidOperation as exc:
        raise InputError(f"{path} is not a valid decimal") from exc
    if not number.is_finite():
        raise InputError(f"{path} must be finite")
    if number < 0 or (positive and number == 0):
        comparison = "greater than zero" if positive else "nonnegative"
        raise InputError(f"{path} must be {comparison}")
    return number


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY, rounding=ROUND_HALF_UP), "f")


def calculate(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    require_exact_keys(data, TOP_LEVEL_KEYS, "input")
    tax_year = tax_year_field(data["tax_year"])
    beginning = decimal_field(data["beginning_principal"], "beginning_principal")
    ending = decimal_field(data["ending_principal"], "ending_principal")
    interest = decimal_field(data["interest_paid"], "interest_paid")
    qualified_loan_limit = decimal_field(
        data["qualified_loan_limit"], "qualified_loan_limit", positive=True
    )

    eligibility = data["eligibility"]
    if not isinstance(eligibility, dict):
        raise InputError("eligibility must be a JSON object")
    require_exact_keys(eligibility, ELIGIBILITY_KEYS, "eligibility")
    for gate in sorted(ELIGIBILITY_KEYS):
        if not isinstance(eligibility[gate], bool):
            raise InputError(f"eligibility.{gate} must be a JSON boolean")

    failed_gates = sorted(gate for gate in ELIGIBILITY_KEYS if not eligibility[gate])
    if failed_gates:
        return 3, {
            "status": "escalation",
            "tax_year": tax_year,
            "error": {
                "code": "unsupported_mortgage_case",
                "message": (
                    "The average-of-first-and-last-balance method is not supported "
                    "for this mortgage. Use the applicable Publication 936 method."
                ),
                "failed_gates": failed_gates,
            },
        }

    average_balance = (beginning + ending) / Decimal(2)
    if average_balance == 0:
        if interest != 0:
            raise InputError(
                "interest_paid must be zero when the average mortgage balance is zero"
            )
        ratio = Decimal("1.000")
    else:
        unrounded_ratio = min(Decimal(1), qualified_loan_limit / average_balance)
        ratio = unrounded_ratio.quantize(RATIO, rounding=ROUND_HALF_UP)

    deductible = (interest * ratio).quantize(MONEY, rounding=ROUND_HALF_UP)
    interest_rounded = interest.quantize(MONEY, rounding=ROUND_HALF_UP)
    nondeductible = interest_rounded - deductible

    return 0, {
        "status": "ok",
        "tax_year": tax_year,
        "calculation": "publication_936_average_balance_shortcut",
        "result": {
            "average_mortgage_balance": money(average_balance),
            "qualified_loan_limit": money(qualified_loan_limit),
            "deductible_ratio": format(ratio, ".3f"),
            "interest_paid": money(interest),
            "deductible_mortgage_interest": money(deductible),
            "nondeductible_mortgage_interest": money(nondeductible),
        },
        "assumptions": sorted(ELIGIBILITY_KEYS),
        "warnings": [
            "The deductible ratio is rounded to three decimal places before it is applied."
        ],
    }


def emit(payload: dict[str, Any], *, stream: Any) -> None:
    print(json.dumps(payload, sort_keys=True), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(
        description="Calculate deductible interest for one eligible acquisition-debt mortgage.",
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
