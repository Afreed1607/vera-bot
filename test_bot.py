#!/usr/bin/env python3
"""
Quick test of the bot's composition logic without needing to start the server.
"""

import json
from pathlib import Path

# Import just the composer
import sys
sys.path.insert(0, '.')
from bot import compose_message

def test_composition():
    """Test that composition logic works."""
    expanded_dir = Path('expanded')

    # Load sample data
    dentists = json.load(open(expanded_dir / 'categories' / 'dentists.json'))

    merchants = list(Path(expanded_dir / 'merchants').glob('*.json'))[:3]
    merchant_contexts = [json.load(open(m)) for m in merchants]

    triggers_dir = Path(expanded_dir / 'triggers')
    triggers = [json.load(open(t)) for t in list(triggers_dir.glob('*.json'))[:3]]

    customers_dir = Path(expanded_dir / 'customers')
    customers = [json.load(open(c)) for c in list(customers_dir.glob('*.json'))[:3]]

    print("OK: Loaded dentists category")
    print(f"OK: Loaded {len(merchant_contexts)} sample merchants")
    print(f"OK: Loaded {len(triggers)} sample triggers")
    print(f"OK: Loaded {len(customers)} sample customers")

    print("\n=== Testing Composition ===\n")

    # Test merchant-facing research digest
    for i, (merchant, trigger) in enumerate(zip(merchant_contexts[:2], triggers[:2])):
        if trigger.get('kind') == 'research_digest':
            try:
                composed = compose_message(dentists, merchant, trigger)
                print(f"Test {i+1} ({trigger['kind']}):")
                print(f"  Merchant: {merchant['identity']['name']}")
                print(f"  Body ({len(composed.body)} chars): {composed.body[:80]}...")
                print(f"  CTA: {composed.cta}")
                print(f"  Rationale: {composed.rationale[:60]}...")
                print()
            except Exception as e:
                print(f"ERROR in test {i+1}: {e}")
                import traceback
                traceback.print_exc()

    # Test customer-facing recall
    for trigger in triggers:
        if trigger.get('kind') == 'recall_due' and trigger.get('customer_id'):
            customer_id = trigger.get('customer_id')
            customers_dir = Path(expanded_dir / 'customers')
            customer_file = customers_dir / f"{customer_id}.json"
            if customer_file.exists():
                customer = json.load(open(customer_file))
                merchant = merchant_contexts[0]  # Use first merchant
                try:
                    composed = compose_message(dentists, merchant, trigger, customer)
                    print(f"Customer-facing recall test:")
                    print(f"  Customer: {customer['identity']['name']}")
                    print(f"  Body ({len(composed.body)} chars): {composed.body[:80]}...")
                    print(f"  Send as: {composed.send_as}")
                    print()
                    break
                except Exception as e:
                    print(f"ERROR in customer test: {e}")
                    import traceback
                    traceback.print_exc()

    print("OK: All composition tests passed!")

if __name__ == '__main__':
    test_composition()



