# Next-year tax handoff

Use at the end of an authorized preparation task or when starting from a prior-year handoff. The handoff is a durable index of facts and continuity items, not a new return or an assertion that earlier work was correct.

## Establish the evidence boundary

Record the source tax year and intended next tax year explicitly. Separately record user-reported submission, IRS acceptance/rejection, and whether the actual filed return was reviewed. A submitted return is not automatically accepted; acceptance is not a merits review. A draft does not become a filed copy when the user says they submitted.

Ask for the saved filed return with relevant schedules, depreciation/carryover worksheets, and any acceptance acknowledgment. Do not block a useful provisional handoff while awaiting it. Label draft amounts as draft, keep filed amounts and opening balances unknown where unsupported, and record exactly which missing document resolves each item. Do not promote modeled zero carryovers into established next-year balances.

## Private artifacts

Create a readable `.tax_work/year-handoff-YYYY-to-YYYY.md` and, when useful for another agent, matching structured JSON. Use one revision for both. Put a status banner and a short next-year starting checklist first. Retain provenance (file, form/line, user statement, revision/date) for each material amount; use source hashes when practical to detect changed files. The source hash establishes file identity, not tax correctness.

Suggested JSON sections: `source_tax_year`, `target_tax_year`, `revision`, `filing_status`, `sources`, `return_summary`, `assets`, `carryforwards`, `next_year_contributions`, `open_items`, and `next_year_start`. Entries should distinguish a document-backed/user-reported value, a calculated draft amount, a verified filed amount and unknown. Preserve amounts as decimal strings or null. Scope records to their year and participant; avoid bare numbers with ambiguous ownership/year.

Do not copy SSNs, full account numbers, addresses, IP PINs, signatures, bank details or raw tax-document text into the handoff. Store it only in the user's authorized private workspace. Use synthetic examples in reusable code/tests; never embed an actual household's return in the skill or shared memory. Warn before exporting to a different storage location.

## Include only continuity items supported by the case

- **Return baseline:** filing status; key income/AGI/tax/withholding/refund lines; actual filed values versus separate draft comparisons. Include prior-year AGI needed by the next filing workflow and total tax potentially relevant to estimated-tax work, without assuming a future calculation.
- **Tax-year bridge:** refund applied forward versus cash refund; estimated/extension payments by date and year; state refunds and the prior itemized-deduction facts needed to evaluate them. Do not equate a federal refund with a state refund, or a loss carryover with a payment credit.
- **Assets:** owner/activity, acquisition and service dates, original cost/land allocation, business-use history, elections, method/recovery period/convention, each year's depreciation and cumulative allowed/allowable basis adjustments. Separate filed depreciation, computed allowable amounts and known errors. Retain improvement history even if omitted from a prior draft. Do not restart an asset or repeat its first-year bonus solely because a new return is being prepared; consult applicable instructions for continuing use, changed use, disposition or corrections.
- **Carryovers/basis:** identify only triggered capital-loss, QBI, home-office, Section 179, credit/AMT, passive-loss, NOL and IRA-basis records. Give each origin year and destination year. Prior-year incoming carryovers do not establish outgoing carryovers. Missing is not zero; zero needs a source or explicit user confirmation for the relevant year.
- **Retirement/HSA:** preserve contribution date separately from tax year, participant and employee/employer source; remaining uncertain splits, correction history and next-year contributions already made. Do not deduct an amount in both years or assume a custodian adjustment establishes its full tax treatment.
- **Fresh annual inputs:** list documents/accounts expected next year, but do not roll forward last year's earnings, expenses, mileage, business-use percentage, coverage eligibility, dependents, residency or withholding as current facts.
- **Decisions and unresolved issues:** describe elections actually evidenced, choices only modeled, superseded interpretations, material source gaps and the precise record needed. An old unresolved issue is a review item, not automatic authorization to amend a submitted return.

Keep the main handoff compact, linking to the detailed audit instead of duplicating the whole return. An ordinary W-2 filer does not need empty specialist sections or a new exhaustive interview.

## Update and reuse

When the filed PDF arrives, reconcile it to the draft and record actual differences and carryovers; retain both versions. Preserve any known calculation concern rather than treating a filed value as legally correct solely because it was filed. Ask before performing an amendment or other materially different action.

If the user says they filed using the draft, record that as user-reported filing amounts tied to the exact draft revision/hash. Do not present them as PDF-verified, infer answers to fields the draft left unknown, or silently apply that confirmation to later draft edits. Separate actual filed rendering/rounding from the calculation's audit precision.

At next-year intake, validate source availability and any amendments, acceptance changes or corrected forms. Re-read exact target-year IRS instructions and current platform behavior. Prefer the filed return and supporting records over a handoff summary, resolve conflicts explicitly, and use the handoff to avoid repeating settled historical questions. Annual limits, rates and line labels must not be copied from the prior year unchecked.

## Validation

Check before delivering:

1. Markdown and JSON agree, and source/target years are distinct and intentional.
2. User-reported submission alone has not filled acceptance, filed amounts or opening-balance fields.
3. Every nonzero or zero carryover has year-specific evidence; unknown balances remain null.
4. Draft depreciation and contribution allocations remain distinguishable from filed/evidenced values, and combined multi-year entries are not guessed into a split.
5. No prior-year rate or annual expense is presented as a new-year input; no private identifiers entered the reusable skill.

A missing filed copy should produce a provisional handoff with targeted follow-up, not fabricated certainty or a refusal to preserve useful context.
