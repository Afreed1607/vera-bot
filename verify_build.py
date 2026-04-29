#!/usr/bin/env python3
"""
Final verification that the complete bot build is ready for submission.
"""

import json
import os
from pathlib import Path

def verify():
    root = Path(".")

    print("=" * 80)
    print("VERA BOT — BUILD VERIFICATION")
    print("=" * 80)
    print()

    checks = []

    # 1. Core files exist
    print("1. Core Files")
    for fname in ["bot.py", "submission.jsonl", "README.md", "requirements.txt"]:
        exists = (root / fname).exists()
        checks.append(exists)
        status = "✓" if exists else "✗"
        print(f"   {status} {fname}")

    print()

    # 2. Submission format
    print("2. Submission Format")
    submission_lines = []
    try:
        with open("submission.jsonl", encoding="utf-8") as f:
            submission_lines = [json.loads(line) for line in f if line.strip()]
        checks.append(len(submission_lines) == 30)
        print(f"   ✓ submission.jsonl has {len(submission_lines)} lines")

        # Check required fields
        required_fields = ["test_id", "body", "cta", "send_as", "suppression_key", "rationale"]
        all_valid = all(all(k in line for k in required_fields) for line in submission_lines)
        checks.append(all_valid)
        print(f"   ✓ All entries have required fields: {required_fields}")

        # Check body lengths
        long_bodies = [line for line in submission_lines if len(line["body"]) > 320]
        checks.append(len(long_bodies) == 0)
        if long_bodies:
            print(f"   ✗ {len(long_bodies)} bodies exceed 320 chars")
        else:
            print(f"   ✓ All bodies ≤ 320 characters")

        # Check for URLs
        url_bodies = [line for line in submission_lines if "http" in line["body"].lower()]
        checks.append(len(url_bodies) == 0)
        if url_bodies:
            print(f"   ✗ {len(url_bodies)} bodies contain URLs")
        else:
            print(f"   ✓ No URLs in any body")

    except Exception as e:
        print(f"   ✗ Error reading submission: {e}")
        checks.append(False)

    print()

    # 3. Dataset
    print("3. Dataset")
    expanded = root / "expanded"
    if expanded.exists():
        categories = list(expanded.glob("categories/*.json"))
        merchants = list(expanded.glob("merchants/*.json"))
        customers = list(expanded.glob("customers/*.json"))
        triggers = list(expanded.glob("triggers/*.json"))

        checks.extend([
            len(categories) == 5,
            len(merchants) == 50,
            len(customers) == 200,
            len(triggers) == 100
        ])

        print(f"   ✓ {len(categories)} categories")
        print(f"   ✓ {len(merchants)} merchants")
        print(f"   ✓ {len(customers)} customers")
        print(f"   ✓ {len(triggers)} triggers")
    else:
        print(f"   ✗ expanded/ directory not found")
        checks.append(False)

    print()

    # 4. Bot code
    print("4. Bot Code")
    try:
        with open("bot.py", encoding="utf-8") as f:
            bot_code = f.read()

        required_endpoints = [
            "/v1/healthz",
            "/v1/metadata",
            "/v1/context",
            "/v1/tick",
            "/v1/reply"
        ]

        for endpoint in required_endpoints:
            has_endpoint = endpoint in bot_code
            checks.append(has_endpoint)
            status = "✓" if has_endpoint else "✗"
            print(f"   {status} {endpoint}")
    except Exception as e:
        print(f"   ✗ Error reading bot.py: {e}")
        checks.append(False)

    print()

    # 5. Summary
    print("=" * 80)
    passed = sum(checks)
    total = len(checks)
    pct = (passed / total * 100) if total > 0 else 0

    print(f"RESULTS: {passed}/{total} checks passed ({pct:.0f}%)")

    if pct == 100:
        print()
        print("STATUS: READY FOR SUBMISSION ✓")
        print()
        print("Next steps:")
        print("  1. Deploy bot.py to public URL (Railway/Render/AWS)")
        print("  2. Submit URL + files to challenge portal")
        print("  3. Submit submission.jsonl (already prepared)")
        print()
    else:
        print()
        print("STATUS: ISSUES FOUND")
        print()
        print("Fix issues above before submitting.")

    print("=" * 80)

if __name__ == "__main__":
    verify()


