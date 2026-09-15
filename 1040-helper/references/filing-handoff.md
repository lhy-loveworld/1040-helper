# Filing reference and controlled updates

Use when generating a filing reference or revising one after new facts. Keep the detailed audit trail behind a short, usable entry checklist.

## A value is not necessarily an instruction to type it

Establish the platform from context or ask once. If it is undecided, produce a platform-neutral reference and mark entry behavior unverified. Check the platform's return-year documentation before identifying automatic fields. Do not assume a form attached in a fillable-forms product transfers every calculated value.

For each relevant row retain:

| Field | Purpose |
|---|---|
| Stable ID | Form, line and participant/activity; distinguish separate spouse forms |
| Amount | Decimal value or unknown, never a guessed zero |
| Action | `manual`, `transfer`, `calculated`, or `reference` |
| Status | `confirmed`, `calculated`, `conditional`, or `unknown` |
| Source | Document/worksheet provenance plus platform authority for action |
| Dependencies | Source facts/lines required to calculate or validate this row |

Action and confidence are separate: a manual field can still have a conditional amount. Put all manual fields first, with unresolved ones visibly marked, then explain transfers and comparisons. For guided software, identify the source-document/interview input instead of instructing a second entry of its form total. Show components of combined deductions without turning them into additional deductions.

For example, a retirement deduction may need manual entry even though half-SE tax transfers and the adjustments total calculates automatically. Verify the actual line numbers and behavior for that year/platform. Do not tell the user to override the total to match the reference. Sources such as [IRS Free File Fillable Forms line instructions](https://www.irs.gov/e-file-providers/line-by-line-instructions-free-file-fillable-forms) are platform guidance, not substitutes for tax-law instructions.

## Whole-dollar filing mode

For Free File Fillable Forms, generate the filing reference using whole-dollar monetary fields, not independently rounded displays of an unrounded return. Keep source cents in a separate audit record. The normalized source amount, intermediate calculation and final filing amount are distinct values; label them and preserve each step's input IDs and rounding rule.

1. Use decimal arithmetic with half-up rounding for dollar fields: fractions below 0.50 drop; 0.50 and above round up in magnitude, preserving the sign. Do not use Python's default ties-to-even `round()`. Normalize negative zero to zero; unknown is still unknown.
2. When several source amounts contribute to **one entry field**, add them with cents and round the combined entry once. Do not round each receipt or source document before aggregation merely because the destination form uses whole dollars.
3. When amounts occupy **different monetary fields**, round at each field boundary. Calculate subsequent fields from those filed/entered amounts, then round each resulting dollar field. For example, separately entered proceeds and basis feed the gain field; do not independently recalculate the gain from raw cents after those inputs have been rounded.
4. Preserve required precision for percentages, fractions, rates, mileage, shares and other non-dollar inputs. Follow explicit worksheet-specific precision instructions for intermediate computations; this is not permission to round every intermediate number to an integer.
5. Transfer a completed form-line value unchanged to its consumers, including manual-transfer fields. Totals must use the same rounded upstream values as the platform. For a rule such as Form 8960 line 5a equaling Form 1040 capital gain plus Schedule 1 other gains, compare the actual filing values exactly after confirming the rule/year and any applicable exception. Do not independently round a raw investment-income calculation for a consumer field.
6. Recompute affected AGI, deductions, income-tax worksheet and additional-tax totals after a filing input changes. If a calculator cannot represent the required intermediate rounding, use an explicit line-by-line adapter/worksheet; rounding its final output is not a substitute. Clearly identify tax fields the platform requires the user to calculate and enter manually.

The entry checklist's primary numbers must be the integer filing values. Cents-based comparisons belong in the audit, not a competing set of numbers to type. Before resubmission, reconcile the completed forms and run `check_rows(rows, whole_dollars=True)` with monetary form rows and applicable equality dependencies. Treat a mismatch as a reconciliation issue even if only one or two dollars; do not change a correct source merely to force agreement. Rounding checks do not validate the underlying tax calculation or prove IRS acceptance.

Implementation helpers in [filing_rounding.py](../scripts/filing_rounding.py), usable from a local form generator:

- `form_dollars(value)`: round one monetary field, return an integer decimal string; null stays null.
- `source_sum_to_form(values)`: sum source cents for ONE destination entry, then round once.
- `sum_form_dollars(values)`: sum already-rounded monetary fields; reject fractional inputs to prevent accidentally mixing source and filing values.

These functions accept decimal strings/`Decimal`, reject floats and nonfinite values, and do not mutate inputs. A transfer should reuse the producer's filing string rather than call the source aggregator again. Keep rates outside these monetary helpers. `check_rows` uses `amount` as the **filing amount** in this mode; retain raw cents as separate metadata or `reference` rows. `sum_of` checks sum existing filing fields; it is not the source-aggregation adapter. Model non-dollar ratios/rates as audit/reference data outside the monetary entry check.

Authority checked September 14, 2026: [2025 Form 1040 instructions, Rounding Off to Whole Dollars](https://www.irs.gov/instructions/i1040gi) specify consistent whole-dollar rounding and aggregation of cents before rounding a single entry. [Free File Fillable Forms line instructions](https://www.irs.gov/e-file-providers/line-by-line-instructions-free-file-fillable-forms) identify manual/calculated fields; verify the target-year platform's specific field behavior. This mode addresses the observed whole-dollar workflow and must not be silently imposed on another platform or on nonmonetary fields.

## Change handling

Maintain one current revision and explicit scenario identity in normalized inputs, traces and generated references. Preserve prior versions or a reproducible change history. Never overwrite user-edited artifacts blindly; merge or flag the overlap.

1. Classify the new statement: additional transaction, replacement value, reconfirmation, or presentation-only change. Use stable expense/transaction IDs. A repeated annual maintenance total is not another expense; if ambiguous, ask before adding it.
2. Update only supported facts. For an ambiguous contribution allocation, keep the year split unknown rather than overwriting the current scenario with a guessed allocation.
3. Determine affected lines transitively. A retirement deduction change can affect adjustments, AGI, QBI, taxable income and tax while leaving Schedule C profit unchanged. Dependencies include limit/eligibility inputs, not just arithmetic operands.
4. Recompute affected results or mark them stale/unknown. Within authorized artifact-editing scope, regenerate current JSON, traces and readable reference from the same revision; do not publish a partially updated set as current. For an answer-only request, identify that the file remains unchanged/stale rather than silently editing it.
5. Report changes and unchanged items. If only presentation changed, explicitly say the deduction was already included and no second deduction was added. Do not label a draft as the filed return without the actual filed document.

The small helpers below support these checks; they do not calculate taxes or prove filing readiness. Use them in a local generator or tests by importing [workflow_checks.py](../scripts/workflow_checks.py). They have no file/network side effects:

- `check_rows(rows)` checks IDs/dependencies, confidence, optional `sum_of` arithmetic, and returns manual entries and issues. Each row uses the fields above; optional `sum_of` lists IDs to add. Amounts are strings or null, and `depends_on` is a list of row IDs. Include source-fact rows as `reference`. Manual entries with unresolved inputs remain visible but are not marked ready.
- `affected_lines(rows, changed_ids)` returns the transitive affected set, including changed IDs, independent of row order. Missing IDs or cycles raise `ValueError`.
- `check_revisions(current_revision, artifact_revisions)` identifies artifacts generated from a different revision. It does not establish that a claimed revision was actually regenerated.
- `reconcile_contributions(before, after)` accepts principal snapshot entries with `id`, `participant`, `deposit_date` (ISO date), `amount` (nonnegative decimal string), `year` (integer or null), `kind` (`employee`, `employer`, or `unknown`), `evidence`, and `year_evidence` (required for known years). It compares totals and reports known buckets and unresolved entries. Caller must explain nonzero principal differences; zero difference alone does not validate a tax correction.

## Regression cases

Use synthetic facts and behavioral assertions rather than copying a taxpayer's records or checking only headings:

- A known manual retirement entry appears in the checklist, while its automatic total does not; an unknown required input cannot produce a ready total.
- A combined employer amount spanning unknown years remains unallocated; no year is inferred from deposit date or arithmetic residual.
- Reconfirming an expense produces no changed amount; replacing one invalidates downstream lines without adding another expense.
- Changing a deduction invalidates every dependent QBI/tax/refund result but not unrelated wages or business receipts.
- Mixed artifact revisions are detected; malformed money, missing dependencies and cycles fail visibly.
- Whole-dollar half-up boundaries and negative amounts are correct; source aggregation differs from summing separate form entries where appropriate. A cross-form mismatch caused by independently rounding raw cents is rejected, not tolerated.

These checks complement exact-year calculation tests. Passing them does not prove source completeness, correct legal classification, platform mapping or final filing eligibility.
