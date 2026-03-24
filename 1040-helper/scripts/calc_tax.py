import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Calculate Tax Liability based on provided brackets")
    parser.add_argument("--ordinary-income", type=float, required=True, help="Your total ordinary taxable income")
    parser.add_argument("--preferential-income", type=float, required=True, help="Qualified Divs + LT Cap Gains")
    parser.add_argument("--brackets", type=str, required=True, help="JSON string of ordinary tax brackets. Format: [{'rate': 0.10, 'up_to': 23850}, {'rate': 0.12, 'up_to': 96950}]")
    parser.add_argument("--pref-brackets", type=str, required=True, help="JSON string of preferential tax brackets. Format: [{'rate': 0.0, 'up_to': 96950}, {'rate': 0.15, 'up_to': 593400}]")
    
    args = parser.parse_args()

    try:
        brackets = json.loads(args.brackets)
        pref_brackets = json.loads(args.pref_brackets)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON brackets: {e}")
        return

    # Sort brackets by 'up_to' just in case, treating missing 'up_to' as infinity
    brackets = sorted(brackets, key=lambda x: x.get('up_to', float('inf')))
    pref_brackets = sorted(pref_brackets, key=lambda x: x.get('up_to', float('inf')))

    # Calculate Ordinary Tax
    ordinary_tax = 0.0
    previous_limit = 0.0
    remaining_income = args.ordinary_income

    for b in brackets:
        rate = b['rate']
        up_to = b.get('up_to', float('inf'))
        
        chunk = up_to - previous_limit
        if remaining_income > 0:
            taxable_chunk = min(remaining_income, chunk)
            ordinary_tax += taxable_chunk * rate
            remaining_income -= taxable_chunk
        previous_limit = up_to

    # Calculate Preferential Tax (stacks on top of ordinary income)
    pref_tax = 0.0
    total_base_income = args.ordinary_income
    remaining_pref = args.preferential_income
    previous_limit = 0.0
    
    for b in pref_brackets:
        rate = b['rate']
        up_to = b.get('up_to', float('inf'))
        
        if up_to <= total_base_income:
            previous_limit = up_to
            continue
            
        chunk_available = up_to - max(previous_limit, total_base_income)
        
        if remaining_pref > 0 and chunk_available > 0:
            taxable_chunk = min(remaining_pref, chunk_available)
            pref_tax += taxable_chunk * rate
            remaining_pref -= taxable_chunk
            total_base_income += taxable_chunk
            
        previous_limit = up_to

    total_tax = ordinary_tax + pref_tax
    print(f"Tax on Ordinary Income: ${ordinary_tax:,.2f}")
    print(f"Tax on Preferential Income: ${pref_tax:,.2f}")
    print(f"Total Federal Tax: ${total_tax:,.2f}")

if __name__ == "__main__":
    main()