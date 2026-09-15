# Calculator inputs

Use these schemas only after the workflow has selected the matching exact-year IRS method. The calculators contain no tax-year constants. Put the applicable year, limits, thresholds, and official lookup results in the input JSON and record their sources in `.tax_work/rules-manifest.json`.

Pass one JSON file with `--input`. Represent money and rates as decimal strings to preserve exact values. Every input requires `tax_year` as a positive integer. Unknown or missing fields fail validation.

- Exit `0`: JSON result on stdout.
- Exit `2`: invalid or incomplete input as JSON on stderr.
- Exit `3`: unsupported case requiring another official worksheet as JSON on stderr.

## Income tax

Run `scripts/calc_tax.py` in one of two modes.

### Ordinary mode

Provide exactly:

- `tax_year`
- `mode`: `ordinary`
- `taxable_income`
- `ordinary_tax`: one of the ordinary-tax sources below

### Qualified-dividends/capital-gain mode

Provide exactly:

- `tax_year`
- `mode`: `qualified_dividends_capital_gain`
- `taxable_income`
- `qualified_dividends`: the exact worksheet line 2 amount
- `worksheet_line_3_capital_gain`: the exact worksheet line 3 amount
- `zero_rate_threshold` and `fifteen_rate_threshold`: exact-year worksheet values for the filing status
- `ordinary_tax`: a source that covers both ordinary taxable income and total taxable income
- `eligibility`: all required booleans below

Eligibility keys:

- `schedule_d_tax_worksheet_not_required`
- `form_4952_adjustment_not_required`
- `no_28_percent_rate_gain`
- `no_unrecaptured_section_1250_gain`
- `form_2555_not_required`
- `form_8615_not_required`

If any value is false, use the alternate worksheet identified by the return-year instructions.

### Ordinary-tax sources

Choose only the source required for each income amount by the exact-year instructions:

- `brackets`: `{"type":"brackets","brackets":[...]}`. Each row contains `up_to` and `rate`; use `null` for the final open-ended limit. Use this only when rate-schedule arithmetic is the prescribed method for every amount the calculation requests.
- `table`: `{"type":"table","rows":[...]}`. Each official lookup row contains `at_least`, `less_than`, and `tax`. Rows may be sparse, but every income requested by the calculation must fall in exactly one supplied row.
- `values`: `{"type":"values","values":[...]}`. Each row contains an exact `income` and its `tax`, obtained using the IRS-prescribed method. Prefer this when a qualified-dividend worksheet needs ordinary-tax results calculated by different methods on different lines.

The output is income tax before credits and additional taxes, not total federal tax.

## Mortgage interest

Run `scripts/calc_mortgage.py` only for one simple acquisition-debt mortgage using the Publication 936 average-of-first-and-last-balance method.

Provide exactly:

- `tax_year`
- `beginning_principal`, `ending_principal`, `interest_paid`, and the `qualified_loan_limit` determined under the exact-year Publication 936 worksheet
- `eligibility` with all of these set from the loan records: `single_mortgage`, `no_new_borrowing`, `no_principal_prepayment_over_one_month`, `level_payments`, `qualified_home`, `debt_used_to_buy_build_or_improve`, and `single_debt_category`

A false gate returns an escalation to the applicable Publication 936 method. The calculator rounds the deductible ratio to three decimal places before applying it, following the worksheet.

## State or local income-tax refund

Run `scripts/calc_state_refund.py` only for the simple recovery case covered by the return-year State and Local Income Tax Refund Worksheet. Here, `tax_year` is the year in which the refund is reported; all deduction inputs come from the corresponding prior-year return.

Provide exactly:

- `tax_year` and `refund_amount`
- `prior_income_tax_deduction`
- `total_salt_paid` and `allowed_salt_deduction`
- `total_itemized_deductions` and `applicable_standard_deduction`, including any applicable additional standard-deduction amount
- `eligibility`: `immediately_preceding_year`, `itemized_deductions`, `deducted_state_and_local_income_tax`, `no_alternative_minimum_tax`, `no_unused_tax_credits`, `no_exception_cases`, and `same_filing_unit`

The calculator returns zero when the taxpayer did not itemize or did not deduct state and local income tax. Other failed gates escalate. Set `no_exception_cases` to false when the exact-year instructions redirect to the broader recovery rules, including an unusual refund type or year, a zero-tax capital-gain case, a late prior-year estimated payment, a dependent or married-filing-separately exception, or another listed exception.
