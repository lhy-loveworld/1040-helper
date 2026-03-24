import argparse

def main():
    parser = argparse.ArgumentParser(description="Calculate Deductible Mortgage Interest")
    parser.add_argument("--beginning-principal", type=float, required=True, help="Mortgage balance at the beginning of the year")
    parser.add_argument("--ending-principal", type=float, required=True, help="Mortgage balance at the end of the year")
    parser.add_argument("--interest-paid", type=float, required=True, help="Total mortgage interest paid in the year")
    parser.add_argument("--irs-limit", type=float, required=True, help="The IRS mortgage principal limit for the year (e.g., 750000)")
    args = parser.parse_args()

    average_balance = (args.beginning_principal + args.ending_principal) / 2.0
    
    if average_balance <= args.irs_limit:
        deductible_interest = args.interest_paid
        ratio = 1.0
    else:
        ratio = args.irs_limit / average_balance
        deductible_interest = args.interest_paid * ratio

    print(f"Average Principal Balance: ${average_balance:,.2f}")
    print(f"Deductible Ratio (Limit / Average Balance): {ratio:.6f}")
    print(f"Allowed Deductible Mortgage Interest: ${deductible_interest:,.2f}")
    print(f"Non-deductible Interest: ${(args.interest_paid - deductible_interest):,.2f}")

if __name__ == "__main__":
    main()