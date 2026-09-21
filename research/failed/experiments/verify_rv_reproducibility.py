"""
Quantitative Crypto Platform (QCP) — Reproducibility Verification Script.
Executes the Relative Value Baseline research pipeline twice under identical inputs and
asserts that every numerical and categorical output matches identically.
"""

import json
import os
import sys
import copy
from research.experiments.run_relative_value_baseline import run_relative_value_baseline


def verify_reproducibility():
    print("=" * 70)
    print("QCP — RESEARCH REPRODUCIBILITY AUDIT")
    print("=" * 70)

    print("Running Baseline Run #1...")
    res_1 = run_relative_value_baseline()

    print("\nRunning Baseline Run #2...")
    res_2 = run_relative_value_baseline()

    # Compare excluding generated_utc
    c1 = copy.deepcopy(res_1)
    c2 = copy.deepcopy(res_2)
    c1.pop("generated_utc", None)
    c2.pop("generated_utc", None)

    s1 = json.dumps(c1, sort_keys=True)
    s2 = json.dumps(c2, sort_keys=True)

    if s1 != s2:
        print("❌ REPRODUCIBILITY FAILURE: Run #1 and Run #2 differ!")
        # Find differences
        for k in c1:
            if c1[k] != c2.get(k):
                print(f"Difference in key: {k}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ REPRODUCIBILITY VERIFIED: Run #1 and Run #2 match bit-for-bit!")
    print(f"Total evaluated pairs: {len(c1.get('pairs_evaluated', {}))}")
    print(f"Summary metrics match: {c1.get('summary')}")
    print("=" * 70)


if __name__ == "__main__":
    verify_reproducibility()
