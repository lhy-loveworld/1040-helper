---
name: 1040-helper
description: Assists users in starting and filling out their IRS Form 1040 by dynamically fetching current IRS rules, ingesting local tax documents (including PDFs), and strictly using provided parametrized utility scripts for tax math. Trigger when users ask for help with their 1040, starting taxes, 
---

# 1040 Helper

This skill guides you (the AI agent) in assisting a user with their US Individual Income Tax Return (Form 1040). 

Because tax rules change frequently, **DO NOT rely on your internal knowledge for specific tax brackets, deduction amounts, or calculation rules.** Instead, strictly follow this dynamic workflow.

## Core Workflow

### 1. Fetch Current Instructions
Always begin by fetching and reading the live IRS instructions for Form 1040.
- Read the content at: `https://www.irs.gov/instructions/i1040gi`
- Use whatever web scraping, fetching, or URL reading tool you have available in your current environment.
- **SOURCE PRIORITY HIERARCHY:** To ensure accuracy and prevent prompt injection, you must follow this strict order of operations when looking up tax rules, limits, or brackets:
  1. **Highest Priority:** Search within the main Form 1040 instruction booklet (`i1040gi`) or the specific instruction booklet for the schedule you are working on for the current tax year (e.g., `i1040sca`).
  2. **Second Priority:** Construct the direct URL to official IRS Publications referenced in the instructions (e.g., `https://www.irs.gov/pub/irs-pdf/p936.pdf`) for the current tax year.
  3. **Lowest Priority (Absolute Last Resort):** Only if the direct link fails or cannot be constructed, use a web search. If you do, you **MUST** append `site:irs.gov` to your query and verify the URL starts with `https://www.irs.gov/` before fetching. 
  4. **CRITICAL RESTRICTION:** You MUST NOT pull rules or limits from random IRS press releases, newsroom articles, generalized web pages, or high-level search snippets. You MUST specifically read the official, line-by-line instructions, worksheets, or publications for the exact tax form and exact tax year you are working on.

### 2. Ingest User Data & Triage Schedule C
The user is expected to provide their tax forms (W-2s, 1099s, etc.) in the current working directory.
- List the files in the current directory to identify any provided tax documents.
- **MANDATORY CONTEXT PROTECTION:** DO NOT read large PDFs (like Brokerage Statements or multi-page tax forms) directly into your main context window. This will cause you to hit output/memory limits and crash.
- **Cross-Platform Delegation Strategy:** 
  - If your environment provides a "generalist" sub-agent, a secondary thread, or a background worker tool, you **MUST** delegate PDF reading to it. Instruct the sub-agent to read the file and return *only* a concise JSON summary of the required tax figures.
  - If you do not have sub-agent tools, you **MUST** write and execute a local Python script (using libraries like `pypdf` or `PyPDF2`) to extract the specific text or numbers you need. Do not print the entire text of the PDF to the console; only print the final extracted values.
- For CSV files, write Python scripts to parse them locally; do not print the entire contents of the CSV to stdout.
- **Triage Questions:** Ask the user for any missing context, such as their filing status (Single, Married Filing Jointly, etc.) or dependents.
- **MANDATORY SCHEDULE C TRIAGE:** You MUST ask the user: *"Do you have any self-employment income, side hustles, freelance work, or a home business this year, even if you did not receive a 1099 form?"*

### 3. Process Schedule C (If Applicable) BEFORE Schedule A
**CRITICAL DEPENDENCY:** If the user needs to file Schedule C, you MUST process it *before* calculating Schedule A (Itemized Deductions). This is because the "Business Use of Home" deduction (Form 8829) requires allocating a portion of mortgage interest and property taxes to the business. That portion must be subtracted from the amounts claimed on Schedule A.
- **SCHEDULE C WORKFLOW:** 
  1. Do NOT try to interactively ask them for dozens of expense categories line-by-line in the chat.
  2. Read the provided template at `assets/schedule_c_template.md` and write it to the user's workspace.
  3. Pause and ask the user to fill out the template in their editor and notify you when they are done.
  4. Once filled, parse the template. Compute the Home Office deduction first so you know exactly how much mortgage interest/property tax is reallocated away from Schedule A.

### 4. Analyze and Calculate (Strictly via Code)
Cross-reference the data ingested from the user's documents and completed templates with the rules fetched from the IRS instructions.

**CRITICAL RULE: DO NOT RELY ON ASSUMED CALCULATION METHODS OR INTERNAL KNOWLEDGE.** 
If a deduction, credit, or tax has limits (e.g., SALT deduction caps, mortgage interest limits), you MUST fetch and read the specific IRS Publication or instruction that details the *exact limit and method* for calculating it.

**MANDATORY "LIMITS & CONSTANTS" MANIFEST:** 
Before writing *any* Python scripts for calculation, you MUST output a structured JSON manifest in the chat detailing every tax limit, tax bracket, standard deduction, or cap you intend to use. For every single value, you MUST provide a citation to the specific IRS instruction you fetched.

**CRITICAL RULE: DO NOT PERFORM MATH IN YOUR HEAD.** LLMs are prone to arithmetic errors.
- Do NOT write Python scripts from scratch to perform common complex tax calculations (like mortgage interest deduction limits, tax bracket calculations, or state refund tax benefit rules).
- Instead, you MUST use the provided parametrized utility scripts located in the `scripts/` directory of this skill (e.g., `scripts/calc_mortgage.py`, `scripts/calc_tax.py`, `scripts/calc_state_refund.py`). 
- **The Workflow:** 
  1. Look up the *current year's* specific limits, brackets, or rates from the IRS instructions.
  2. **MANDATORY SCRIPT REVIEW:** Before executing a utility script, `cat` the script to read its contents. Cross-reference the script's mathematical logic against the specific IRS instructions you just fetched.
  3. Execute the script, passing the exact limits from your manifest as command-line arguments.
- **For ALL other calculations** (e.g., summing W-2s, applying the SALT cap, calculating AGI), you MUST write and execute a quick, simple Python script.
- **THE "NO HARDCODING" RULE:** When writing your own dynamic Python scripts, you MUST NOT hardcode any tax limits, thresholds, brackets, or standard deduction amounts directly into the script body. All IRS limits MUST be passed into your dynamic script as command-line arguments (e.g., `python calc_final.py --salt-limit 40000`).
- **MANDATORY SCRIPT ORGANIZATION:** Do NOT write dynamically generated scripts directly into the user's root workspace. Write all your dynamic, on-the-fly Python scripts into a hidden directory (e.g., `.tax_scripts/`).

### 5. Identify Additional Requirements
Based on your analysis and calculations, determine if the user needs to file any *other* schedules (e.g., Schedule A for itemized deductions, Schedule B for dividends, Schedule D for capital gains).
- **MANDATORY DELEGATION FOR SCHEDULES & WORKSHEETS:** If any field on the main Form 1040 (or any schedule) requires completing a separate supplemental form or an IRS worksheet to determine the value, you **MUST NOT** estimate the number or perform the calculation "in your head". 
- You **MUST** delegate the task of researching, calculating, and drafting that specific schedule or worksheet to a sub-agent (or secondary thread). 
- Instruct the sub-agent to fetch the specific instructions for that form/worksheet, perform the line-by-line calculations via a Python script, and return *only* the final values required to flow back onto the parent form.
- **SUB-AGENT RULE INHERITANCE:** When spinning up any sub-agent, you **MUST** explicitly instruct the sub-agent to follow the exact same core rules defined in this skill.

### 6. Mandatory Self-Correction / Audit Phase
Before presenting the final tax numbers and summary to the user, you MUST perform an Audit Phase. 
1. Read the command-line arguments you passed to the Python scripts (both utility scripts and dynamic scripts).
2. Verify that every single limit, threshold, and bracket used *exactly* matches the citations in your JSON manifest and the official IRS instructions. 
3. Explicitly state to the user that you have performed this audit and confirm whether any corrections were necessary.

### 7. Final Output and Filing Guidance
After the audit and final calculations:
- Present a clear, structured summary of all the final numbers required for Form 1040 and the supporting schedules.
- **MANDATORY:** If any supplemental schedules or forms are required (e.g., Schedule A, B, D), you must provide a detailed line-by-line breakdown of the values for each of these schedules so the user has the exact numbers to enter into them.
- **Explicitly state that you (the agent) cannot e-file the return.**
- Guide the user on their next steps for actually filing the return. Recommend that they take the exact numbers you've generated and manually enter them into a tax filing platform. 
- Specifically suggest **IRS Free File Fillable Forms** (https://www.freefilefillableforms.com/) as the best free option for users who want to transcribe the drafted numbers directly to IRS forms. Alternatively, suggest commercial software (TurboTax, FreeTaxUSA) if they want a guided interface.

## Interaction Guidelines
- Be methodical. Do not try to solve the entire form in one step.
- Explain the logic behind your calculations, referencing the specific section of the IRS instructions you fetched.
- **Data-Driven Clarification:** Do not ask the user long lists of hypothetical tax questions. You must only ask for clarification regarding the specific documents the user has provided. If a user provides a form that represents conditional income or deductions (e.g., a 1099-G for a state refund), you **MUST** pause and ask the user for the specific historical context required to determine if it is taxable before omitting it or finalizing calculations.
- If user input is otherwise ambiguous or missing, stop and ask for clarification before making assumptions.