import os
import sys
import json
import time

sys.path.insert(0, "/home/mrcn2/crypto-platform")

from research.experiments.run_canonical_replay_engine import run_single_stream

# Test on BTC_SET_3, SOL_SET_3, SOL_SET_4
test_streams = [("BTC", "SET_3"), ("SOL", "SET_4")]

print("--- Testing Pure H0 ---")
for asset, tf in test_streams:
    res = run_single_stream(asset, tf, "H0")
    print(f"H0 {asset}_{tf}: trades={len(res.get('trades', []))}, candidates={len(res.get('all_candidates', []))}")

print("\n--- Testing EXP_TARGET_STRUCTURAL_01 (Current run_canonical_replay_engine settings) ---")
for asset, tf in test_streams:
    res = run_single_stream(asset, tf, "EXP_TARGET_STRUCTURAL_01")
    print(f"EXP {asset}_{tf}: trades={len(res.get('trades', []))}, candidates={len(res.get('all_candidates', []))}")
