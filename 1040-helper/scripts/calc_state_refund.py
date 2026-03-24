import argparse

def main():
    parser = argparse.ArgumentParser(description="Calculate Taxable State Refund using the Tax Benefit Rule")
    parser.add_argument("--prior-year-salt-paid", type=float, required=True, help="Total state and local taxes paid in the prior year")
    parser.add_argument("--prior-year-salt-limit", type=float, required=True, help="The maximum SALT deduction limit for the prior year (e.g. 10000)")
    parser.add_argument("--refund-amount", type=float, required=True, help="The state tax refund amount from 1099-G")
    args = parser.parse_args()

    actual_salt_liability = args.prior_year_salt_paid - args.refund_amount
    
    if actual_salt_liability >= args.prior_year_salt_limit:
        taxable_refund = 0.0
    else:
        # If the actual liability dipped below the claimed limit, the difference is the portion
        # of the refund that provided a tax benefit
        taxable_refund = args.prior_year_salt_limit - actual_salt_liability
        # Ensure we don't return a taxable amount greater than the refund itself
        taxable_refund = min(taxable_refund, args.refund_amount)

    print(f"Prior Year SALT Paid: ${args.prior_year_salt_paid:,.2f}")
    print(f"Prior Year SALT Limit: ${args.prior_year_salt_limit:,.2f}")
    print(f"Actual Liability (Paid - Refund): ${actual_salt_liability:,.2f}")
    print(f"Taxable Amount of Refund: ${taxable_refund:,.2f}")

if __name__ == "__main__":
    main()