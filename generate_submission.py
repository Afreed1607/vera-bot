#!/usr/bin/env python3
"""
Generate submission.jsonl by running the bot's composer on all test pairs.
"""

import json
import sys
from pathlib import Path

# Add bot module to path
sys.path.insert(0, str(Path(__file__).parent))

from bot import compose_message

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_all_contexts(expanded_dir):
    """Load all contexts from expanded directory."""
    contexts = {}

    # Load categories
    categories = {}
    for cat_file in Path(expanded_dir).glob("categories/*.json"):
        data = load_json(cat_file)
        categories[data["slug"]] = data
    contexts["categories"] = categories

    # Load merchants
    merchants = {}
    for m_file in Path(expanded_dir).glob("merchants/*.json"):
        data = load_json(m_file)
        merchants[data["merchant_id"]] = data
    contexts["merchants"] = merchants

    # Load customers
    customers = {}
    for c_file in Path(expanded_dir).glob("customers/*.json"):
        data = load_json(c_file)
        customers[data["customer_id"]] = data
    contexts["customers"] = customers

    # Load triggers
    triggers = {}
    for t_file in Path(expanded_dir).glob("triggers/*.json"):
        data = load_json(t_file)
        triggers[data["id"]] = data
    contexts["triggers"] = triggers

    return contexts

def main():
    expanded_dir = Path(__file__).parent / "expanded"

    print(f"Loading contexts from {expanded_dir}...")
    contexts = load_all_contexts(expanded_dir)

    print(f"Loaded: {len(contexts['categories'])} categories, "
          f"{len(contexts['merchants'])} merchants, "
          f"{len(contexts['customers'])} customers, "
          f"{len(contexts['triggers'])} triggers")

    # Load test pairs
    test_pairs_file = expanded_dir / "test_pairs.json"
    test_pairs_data = load_json(test_pairs_file)
    pairs = test_pairs_data.get("pairs", [])

    print(f"\nComposing for {len(pairs)} test pairs...")

    submissions = []
    for i, pair in enumerate(pairs):
        test_id = pair.get("test_id", f"T{i+1:02d}")
        trigger_id = pair.get("trigger_id")
        merchant_id = pair.get("merchant_id")
        customer_id = pair.get("customer_id")

        # Get contexts
        trigger = contexts["triggers"].get(trigger_id)
        merchant = contexts["merchants"].get(merchant_id)

        if not trigger or not merchant:
            print(f"  {test_id}: SKIP (missing trigger or merchant)")
            continue

        category_slug = merchant.get("category_slug")
        category = contexts["categories"].get(category_slug)

        if not category:
            print(f"  {test_id}: SKIP (missing category)")
            continue

        customer = None
        if customer_id:
            customer = contexts["customers"].get(customer_id)

        # Compose
        try:
            composed = compose_message(category, merchant, trigger, customer)

            submission = {
                "test_id": test_id,
                "body": composed.body,
                "cta": composed.cta,
                "send_as": composed.send_as,
                "suppression_key": composed.suppression_key,
                "rationale": composed.rationale
            }
            submissions.append(submission)
            print(f"  {test_id}: OK ({composed.cta})")
        except Exception as e:
            print(f"  {test_id}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            continue

    # Write submission.jsonl
    output_file = Path(__file__).parent / "submission.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sub in submissions:
            f.write(json.dumps(sub, ensure_ascii=False) + "\n")

    print(f"\n✓ Wrote {len(submissions)} submissions to {output_file}")

if __name__ == "__main__":
    main()

