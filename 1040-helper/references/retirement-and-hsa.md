# Retirement, backdoor Roth, and HSA

Load this module for Forms 1099-R, 5498, 1099-SA, 5498-SA, W-2 retirement/HSA codes, IRA contributions or conversions, rollovers, or HSA distributions.

## IRA and backdoor Roth

Treat “backdoor Roth” as at least two events: an IRA contribution and a Roth conversion. Gather:

- Contribution amount, contribution tax year, date, account type, and whether a deduction was or will be claimed.
- Every Form 1099-R and Form 5498, including late-issued Form 5498 information.
- Prior Forms 8606 and remaining nondeductible basis.
- Exact year-end balances of all traditional, SEP, and SIMPLE IRAs required by the applicable Form 8606 instructions.
- Recharacterizations, returned contributions, rollovers, inherited accounts, and conversions.

Complete the exact-year Form 8606 line by line. Do not assume the conversion is tax-free because contribution and conversion amounts match, and do not omit the aggregation/pro-rata calculation. Reconcile the taxable amount with Form 1099-R coding and the Form 1040 line mapping.

Escalate when prior basis, year-end balances, or rollover history is missing.

## HSA

Gather coverage type and eligible months, age-dependent facts required by the exact-year instructions, employer contributions and payroll deductions from W-2 coding, personal contributions, Forms 1099-SA and 5498-SA, rollovers, excess contributions, and prior carryovers.

For each distribution, obtain the amount of qualified medical expenses that was not reimbursed elsewhere and was incurred after the HSA was established. Do not require receipts in chat; ask the user to retain them and provide only the supported total.

Complete the exact-year Form 8889 and its limitation worksheets. Avoid double-counting payroll contributions as an outside-the-payroll adjustment. Flag excess contributions, nonqualified distributions, inherited HSAs, Medicare enrollment interactions, or incomplete eligibility history for focused review.

## Other distributions

For self-employed owner-only 401(k) contributions or adjustments, load [solo-401k.md](solo-401k.md). Contribution records are not distribution records; do not apply IRA correction rules to a qualified plan by analogy.

For pensions and retirement accounts, preserve payer, account type, gross distribution, taxable amount, distribution code, IRA/SEP/SIMPLE indicator, withholding, rollover amount, basis records, and any disaster or exception facts. Follow the form-specific exact-year instructions; do not infer taxability from the distribution code alone.
