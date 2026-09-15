# Employee equity compensation

Load this module for RSUs, ESPP shares, ISOs, NSOs, Forms 3921/3922, stock-plan statements, or employer securities on Form 1099-B. Also load [capital-gains.md](capital-gains.md) for any disposition.

## Collect only triggered facts

- Employer, plan type, grant identifier, grant/exercise/vest/purchase/sale dates, share counts, and transaction fees.
- Vest or exercise confirmations, purchase records, pay statements, W-2, Forms 3921/3922, Form 1099-B, and the broker's supplemental basis report.
- Whether shares were sold to cover withholding and whether that sale appears separately on Form 1099-B.
- Work locations during the grant-to-vest or grant-to-exercise period when more than one state may claim the income.

Reconcile shares from grant through vest/exercise, withholding sale, transfers, and final sale. Do not combine transactions merely because they share a ticker.

## Route by award

### RSUs

Reconcile the vest-date compensation included in payroll and W-2 wages to the vest statement. Treat a sale—including a same-day sell-to-cover—as a separate disposition. Compare broker-reported basis with the amount supported by payroll and plan records; do not accept blank or zero basis without investigation. Prevent the same compensation from being taxed once as wages and again through unadjusted basis.

### ESPP

Use Form 3922 and plan records to establish grant, purchase, sale, purchase price, and relevant fair-market values. Classify the disposition under the exact-year instructions before calculating compensation and basis. Reconcile any ordinary compensation included in W-2 wages and make the supported Form 8949 basis adjustment.

### ISOs

Separate exercise from sale. An exercise without a same-year disposition may require an AMT adjustment and Form 6251 analysis; do not omit it because no cash was received. Use Form 3921 and plan records to classify a later sale and reconcile regular-tax and AMT basis. Escalate when AMT basis or prior-year minimum-tax-credit records are unavailable.

### NSOs

Reconcile exercise compensation to payroll and W-2 wages. Establish post-exercise basis from plan and payroll records before computing any later sale. Investigate a broker basis that omits compensation already recognized.

## Audit

For each lot, retain the award type, share count, dates, proceeds, broker basis, corrected basis, adjustment reason/code, wage-compensation link, and state-sourcing note. A missing supplemental statement is an unresolved question, not permission to use zero basis.
