# Owner-only 401(k): contributions, deduction and corrections

Load only when a self-employed taxpayer has this plan or asks about contributing or correcting it. This is a workflow, not a table of permanent limits or a custodian-specific correction procedure.

## Keep four questions separate

1. What was deposited or adjusted, and when?
2. Which participant, contribution year and employee/employer source does it belong to?
3. What contribution and deduction are allowed under the executed plan and exact-year rules?
4. If there is an error, what correction procedure actually applies?

A maximum-deductible allocation is not proof of the actual allocation, section 415 excess, or corrective payout. Do not optimize preservation of retirement room automatically: establish the user's objective and compare supported household effects when requested.

## Contribution ledger

Keep original transactions and later adjustments as separate evidence. For each entry record an opaque local ID, participant, deposit/effective date, processing date when different, amount, contribution year, employee/employer source, evidence, and any unresolved allocation. Avoid account numbers in summaries.

- Deposit year and contribution year are distinct. Neither implies the other.
- A generic employer entry can span multiple years. Preserve its combined amount with an unknown year until a supported split is available; do not allocate the residual to the most convenient year.
- Show before/after year-by-source totals, accounting for new deposits, distributions, fees and earnings separately. Net-zero adjustment postings can support a bookkeeping reclassification, not its legal validity.
- Distinguish what a screenshot proves from the user's explanation or a modeled assumption. An exact split requires evidence for each year; simply confirming that both years are included is insufficient.
- Ask one targeted question for the missing split or affected plan term. Do not repeatedly request facts already established or require a full return when a specific field suffices.

The `reconcile_contributions` helper in [workflow_checks.py](../scripts/workflow_checks.py) compares normalized before/after principal snapshots without assigning unknown years. It is not a legal correction check. Do not feed all reversal postings as though they were a final contribution snapshot.

## Calculate the supported deduction

Use the return-year Publication 560 self-employed deduction worksheet and the applicable Schedule SE instructions. Verify relevant adoption/effective-year and election facts, age, other deferrals, eligible earnings and plan terms. For a post-year-end first-year plan, research the applicable exception rather than assuming either validity or invalidity from the opening date.

Record employee and employer components separately, including any limits that bind when earnings are low. Reconcile actual qualifying contributions to the allowed deduction; a worksheet maximum does not establish that the maximum was contributed. Map the owner's deduction to the exact-year adjustment line and the platform's manual-entry field. Do not duplicate workplace deferrals already excluded from W-2 wages or the proprietor's own-plan deduction on Schedule C. Recompute attributable QBI and other dependent values when the supported deduction changes.

## When a correction is involved

Use current administrator records and official IRS guidance applicable to the error, plan year and correction date. Obtain the actual year/source treatment and any distribution or earnings reporting before finalizing affected lines. A service representative's bookkeeping change is evidence of an action, not a blanket tax-law determination.

Do not infer that all deposits made in the following calendar year can be reassigned, that a deduction-capacity gap is an employer refund, or that an IRA return-of-excess form applies. Distinguish reclassification, carryforward, corrective distribution and forfeiture. Check destination-year capacity separately; moving a contribution does not establish enough income in that year. Do not backdate elections or authorize money movement as part of a calculation inquiry.

Research starting points (verify exact revision and relevant passages, then record them in the private rules manifest):

- [Publication 560](https://www.irs.gov/publications/p560): qualified-plan setup, contribution/deduction limits, self-employed worksheet and reporting.
- [One-participant 401(k) plans](https://www.irs.gov/retirement-plans/one-participant-401k-plans): employee/employer roles and self-employed calculations.
- [IRS annual-addition correction guidance](https://www.irs.gov/retirement-plans/fixing-common-plan-mistakes-failure-to-limit-contributions-for-a-participant): correction framework, not authority to reuse dated example limits.
- Participant's executed plan documents and custodian's applicable procedure: evidence for this case, not a universal precedent.
