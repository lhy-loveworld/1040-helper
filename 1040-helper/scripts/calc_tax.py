#!/usr/bin/env python3
"""Calculate ordinary income tax or the simple qualified-dividend/capital-gain worksheet."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, NoReturn


MONEY = Decimal("0.01")
ORDINARY_KEYS = {"tax_year", "mode", "taxable_income", "ordinary_tax"}
PREFERENTIAL_KEYS = ORDINARY_KEYS | {
    "qualified_dividends",
    "worksheet_line_3_capital_gain",
    "zero_rate_threshold",
    "fifteen_rate_threshold",
    "eligibility",
}
PREFERENTIAL_ELIGIBILITY_KEYS = {
    "schedule_d_tax_worksheet_not_required",
    "form_4952_adjustment_not_required",
    "no_28_percent_rate_gain",
    "no_unrecaptured_section_1250_gain",
    "form_2555_not_required",
    "form_8615_not_required",
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


def decimal_field(
    value: Any,
    path: str,
    *,
    maximum: Decimal | None = None,
) -> Decimal:
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
    if maximum is not None and number > maximum:
        raise InputError(f"{path} must not exceed {maximum}")
    return number


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY, rounding=ROUND_HALF_UP), "f")


TaxFunction = Callable[[Decimal], Decimal]


def bracket_tax_function(spec: dict[str, Any]) -> TaxFunction:
    require_exact_keys(spec, {"type", "brackets"}, "ordinary_tax")
    rows = spec["brackets"]
    if not isinstance(rows, list) or not rows:
        raise InputError("ordinary_tax.brackets must be a nonempty JSON array")

    brackets: list[tuple[Decimal | None, Decimal]] = []
    previous_limit = Decimal(0)
    previous_rate = Decimal(0)
    saw_open_end = False
    for index, row in enumerate(rows):
        path = f"ordinary_tax.brackets[{index}]"
        if not isinstance(row, dict):
            raise InputError(f"{path} must be a JSON object")
        require_exact_keys(row, {"up_to", "rate"}, path)
        rate = decimal_field(row["rate"], f"{path}.rate", maximum=Decimal(1))
        if rate < previous_rate:
            raise InputError(f"{path}.rate must not decrease")
        previous_rate = rate

        raw_limit = row["up_to"]
        if raw_limit is None:
            if index != len(rows) - 1:
                raise InputError(f"{path}.up_to may be null only in the final bracket")
            saw_open_end = True
            limit = None
        else:
            limit = decimal_field(raw_limit, f"{path}.up_to")
            if limit <= previous_limit:
                raise InputError(f"{path}.up_to must be greater than the prior limit")
            previous_limit = limit
        brackets.append((limit, rate))

    def tax_for(income: Decimal) -> Decimal:
        tax = Decimal(0)
        lower = Decimal(0)
        remaining = income
        for limit, rate in brackets:
            if remaining <= 0:
                break
            if limit is None:
                amount = remaining
            else:
                amount = min(remaining, limit - lower)
            tax += amount * rate
            remaining -= amount
            if limit is not None:
                lower = limit
        if remaining > 0 and not saw_open_end:
            raise InputError(
                f"ordinary_tax.brackets do not cover taxable income {income}"
            )
        return tax

    return tax_for


def table_tax_function(spec: dict[str, Any]) -> TaxFunction:
    require_exact_keys(spec, {"type", "rows"}, "ordinary_tax")
    raw_rows = spec["rows"]
    if not isinstance(raw_rows, list) or not raw_rows:
        raise InputError("ordinary_tax.rows must be a nonempty JSON array")

    rows: list[tuple[Decimal, Decimal | None, Decimal]] = []
    previous_end: Decimal | None = None
    previous_tax = Decimal(0)
    for index, row in enumerate(raw_rows):
        path = f"ordinary_tax.rows[{index}]"
        if not isinstance(row, dict):
            raise InputError(f"{path} must be a JSON object")
        require_exact_keys(row, {"at_least", "less_than", "tax"}, path)
        start = decimal_field(row["at_least"], f"{path}.at_least")
        if previous_end is not None and start < previous_end:
            raise InputError(f"{path} overlaps or is out of order")
        tax = decimal_field(row["tax"], f"{path}.tax")
        if tax < previous_tax:
            raise InputError(f"{path}.tax must not decrease")
        previous_tax = tax

        raw_end = row["less_than"]
        if raw_end is None:
            if index != len(raw_rows) - 1:
                raise InputError(f"{path}.less_than may be null only in the final row")
            end = None
        else:
            end = decimal_field(raw_end, f"{path}.less_than")
            if end <= start:
                raise InputError(f"{path}.less_than must be greater than at_least")
            previous_end = end
        rows.append((start, end, tax))

    def tax_for(income: Decimal) -> Decimal:
        for start, end, tax in rows:
            if income >= start and (end is None or income < end):
                return tax
        raise InputError(f"ordinary_tax.rows do not cover taxable income {income}")

    return tax_for


def values_tax_function(spec: dict[str, Any]) -> TaxFunction:
    """Return exact ordinary-tax values obtained from the required IRS method."""
    require_exact_keys(spec, {"type", "values"}, "ordinary_tax")
    raw_values = spec["values"]
    if not isinstance(raw_values, list) or not raw_values:
        raise InputError("ordinary_tax.values must be a nonempty JSON array")

    values: dict[Decimal, Decimal] = {}
    for index, row in enumerate(raw_values):
        path = f"ordinary_tax.values[{index}]"
        if not isinstance(row, dict):
            raise InputError(f"{path} must be a JSON object")
        require_exact_keys(row, {"income", "tax"}, path)
        income = decimal_field(row["income"], f"{path}.income")
        tax = decimal_field(row["tax"], f"{path}.tax")
        if income in values:
            raise InputError(f"{path}.income duplicates an earlier income")
        values[income] = tax

    def tax_for(income: Decimal) -> Decimal:
        try:
            return values[income]
        except KeyError as exc:
            raise InputError(
                f"ordinary_tax.values do not include taxable income {income}"
            ) from exc

    return tax_for


def make_tax_function(spec: Any) -> tuple[str, TaxFunction]:
    if not isinstance(spec, dict):
        raise InputError("ordinary_tax must be a JSON object")
    method = spec.get("type")
    if method == "brackets":
        return method, bracket_tax_function(spec)
    if method == "table":
        return method, table_tax_function(spec)
    if method == "values":
        return method, values_tax_function(spec)
    raise InputError("ordinary_tax.type must be 'brackets', 'table', or 'values'")


def calculate(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    mode = data.get("mode")
    if mode == "ordinary":
        require_exact_keys(data, ORDINARY_KEYS, "input")
    elif mode == "qualified_dividends_capital_gain":
        require_exact_keys(data, PREFERENTIAL_KEYS, "input")
    else:
        raise InputError(
            "mode must be 'ordinary' or 'qualified_dividends_capital_gain'"
        )

    tax_year = tax_year_field(data["tax_year"])
    taxable_income = decimal_field(data["taxable_income"], "taxable_income")
    method, tax_for = make_tax_function(data["ordinary_tax"])

    if mode == "ordinary":
        income_tax = tax_for(taxable_income)
        return 0, {
            "status": "ok",
            "tax_year": tax_year,
            "calculation": "ordinary_income_tax",
            "ordinary_tax_source": method,
            "result": {
                "taxable_income": money(taxable_income),
                "income_tax_before_credits_and_additional_taxes": money(income_tax),
            },
            "warnings": [
                "This is an income-tax calculation, not total federal tax."
            ],
        }

    qualified_dividends = decimal_field(
        data["qualified_dividends"], "qualified_dividends"
    )
    capital_gain = decimal_field(
        data["worksheet_line_3_capital_gain"],
        "worksheet_line_3_capital_gain",
    )
    zero_threshold = decimal_field(
        data["zero_rate_threshold"], "zero_rate_threshold"
    )
    fifteen_threshold = decimal_field(
        data["fifteen_rate_threshold"], "fifteen_rate_threshold"
    )
    if fifteen_threshold < zero_threshold:
        raise InputError(
            "fifteen_rate_threshold must be at least zero_rate_threshold"
        )
    reported_preferential_income = qualified_dividends + capital_gain
    # The worksheet limits its preferential-income amount to taxable income.
    # This matters when deductions or ordinary losses make lines 2 + 3 larger
    # than line 1.
    preferential_income = min(taxable_income, reported_preferential_income)

    eligibility = data["eligibility"]
    if not isinstance(eligibility, dict):
        raise InputError("eligibility must be a JSON object")
    require_exact_keys(
        eligibility, PREFERENTIAL_ELIGIBILITY_KEYS, "eligibility"
    )
    for gate in sorted(PREFERENTIAL_ELIGIBILITY_KEYS):
        if not isinstance(eligibility[gate], bool):
            raise InputError(f"eligibility.{gate} must be a JSON boolean")
    failed_gates = sorted(
        gate for gate in PREFERENTIAL_ELIGIBILITY_KEYS if not eligibility[gate]
    )
    if failed_gates:
        return 3, {
            "status": "escalation",
            "tax_year": tax_year,
            "error": {
                "code": "qualified_dividends_capital_gain_worksheet_not_applicable",
                "message": (
                    "The simple Qualified Dividends and Capital Gain Tax Worksheet "
                    "is not supported for this return. Use the indicated alternate "
                    "worksheet or form instructions."
                ),
                "failed_gates": failed_gates,
            },
        }

    ordinary_income = taxable_income - preferential_income
    zero_rate_amount = min(
        preferential_income,
        max(Decimal(0), zero_threshold - ordinary_income),
    )
    remaining = preferential_income - zero_rate_amount
    stacked_after_zero = ordinary_income + zero_rate_amount
    fifteen_rate_amount = min(
        remaining,
        max(Decimal(0), fifteen_threshold - stacked_after_zero),
    )
    twenty_rate_amount = remaining - fifteen_rate_amount

    tax_on_ordinary_income = tax_for(ordinary_income)
    tax_at_fifteen_percent = fifteen_rate_amount * Decimal("0.15")
    tax_at_twenty_percent = twenty_rate_amount * Decimal("0.20")
    tentative_worksheet_tax = (
        tax_on_ordinary_income + tax_at_fifteen_percent + tax_at_twenty_percent
    )
    tax_if_all_ordinary = tax_for(taxable_income)
    worksheet_tax = min(tentative_worksheet_tax, tax_if_all_ordinary)

    return 0, {
        "status": "ok",
        "tax_year": tax_year,
        "calculation": "qualified_dividends_and_capital_gain_tax_worksheet",
        "ordinary_tax_source": method,
        "result": {
            "taxable_income": money(taxable_income),
            "ordinary_taxable_income": money(ordinary_income),
            "reported_qualified_dividends_and_line_3_capital_gain": money(
                reported_preferential_income
            ),
            "preferential_income": money(preferential_income),
            "zero_percent_amount": money(zero_rate_amount),
            "fifteen_percent_amount": money(fifteen_rate_amount),
            "twenty_percent_amount": money(twenty_rate_amount),
            "tax_on_ordinary_income": money(tax_on_ordinary_income),
            "tax_at_fifteen_percent": money(tax_at_fifteen_percent),
            "tax_at_twenty_percent": money(tax_at_twenty_percent),
            "tentative_worksheet_tax": money(tentative_worksheet_tax),
            "tax_if_all_income_were_ordinary": money(tax_if_all_ordinary),
            "income_tax_before_credits_and_additional_taxes": money(worksheet_tax),
        },
        "assumptions": sorted(PREFERENTIAL_ELIGIBILITY_KEYS),
        "warnings": [
            "worksheet_line_3_capital_gain must be the exact amount for line 3 of the return-year Qualified Dividends and Capital Gain Tax Worksheet.",
            "This is an income-tax worksheet result, not total federal tax.",
        ],
    }


def emit(payload: dict[str, Any], *, stream: Any) -> None:
    print(json.dumps(payload, sort_keys=True), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(
        description=(
            "Calculate ordinary income tax or the simple Qualified Dividends "
            "and Capital Gain Tax Worksheet from a JSON file."
        ),
        epilog="Input schemas: see ../references/calculator-inputs.md",
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
