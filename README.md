# 1040 Helper

An AI agent skill designed to assist with preparing the US Individual Income Tax Return (Form 1040). It automates the extraction of tax figures from common documents (W-2s, 1099s, 1098s) and calculates tax brackets, deductions, and liabilities.

## ⚠️ Disclaimer

**I am not a tax professional, CPA, or financial advisor.** This skill is provided for educational and informational purposes only. It is not intended to provide tax, legal, or accounting advice. You should consult your own tax, legal, and accounting advisors before filing your tax return. 

By using this skill, you agree that you are solely responsible for the accuracy of your tax return and any consequences resulting from its filing. The creator of this skill assumes no liability for any errors, omissions, or damages arising from the use of this tool.

## Features
*   **Automated Parsing:** Extracts data from PDFs, CSVs, and Excel files (W-2s, various 1099s, 1098s, Property Tax statements).
*   **Dynamic Rule Fetching:** Fetches current-year IRS instructions and standard deductions dynamically.
*   **Parametrized Calculations:** Uses Python scripts to calculate complex tax limits, like mortgage interest deductions and multi-bracket tax liabilities.

## Usage

1.  **Install the Skill:** Load the `1040-helper` directory into your AI agent environment.
2.  **Gather Documents:** Place your tax documents (W-2s, 1099s, etc.) in a single directory.
3.  **Run the Agent:** Ask the agent to "help me do my 1040" or a similar prompt within the directory containing your tax documents. The agent will activate the skill and guide you through the process.

## Cross-Platform Compatibility

This skill is designed to be cross-platform. It relies on standard Python libraries (`pypdf`, `pandas`, `openpyxl`) which can be installed in a virtual environment on macOS, Linux, or Windows.

## Known Limitations

*   **Schedule C:** The workflow for handling Schedule C (Self-Employment Income) is included in the instructions but **has not yet been thoroughly tested**. Use with caution.
*   **Complex Scenarios:** This tool is optimized for common W-2 and investment income scenarios. Highly complex tax situations may require manual intervention or professional assistance.