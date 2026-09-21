import json
from research.experiments.run_canonical_replay_engine import run_single_stream

print("Running single stream BTC_SET_3 with H0...")
res_h0 = run_single_stream("BTC", "SET_3", "H0")
print(f"H0: status={res_h0['status']} candidates={len(res_h0['all_candidates'])} trades={len(res_h0['trades'])}")

print("\nRunning single stream BTC_SET_3 with PROFIT_LOCK_0.5R_0.25R...")
res_pl = run_single_stream("BTC", "SET_3", "PROFIT_LOCK_0.5R_0.25R")
print(f"PL: status={res_pl['status']} candidates={len(res_pl['all_candidates'])} trades={len(res_pl['trades'])}")
