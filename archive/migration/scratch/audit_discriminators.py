import json
import numpy as np

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

trades = d1["all_trades"]

print(f"Analyzing all 24 executed trades in D1 for key discriminators...")

for t in trades:
    sp = t.get("metadata", {}).get("structural_provenance", {})
    align_ts = sp.get("mtf_alignment_timestamp", 0)
    retest_ts = sp.get("mtf_retest_timestamp", 0)
    conf_ts = sp.get("ltf_confirmation_timestamp", 0)
    
    t["_align_to_retest_hr"] = (retest_ts - align_ts) / 3600.0 if (align_ts and retest_ts) else 0.0
    t["_retest_to_entry_hr"] = (conf_ts - retest_ts) / 3600.0 if (conf_ts and retest_ts) else 0.0
    
    ep = t["entry_price"]
    sl = t["initial_stop_price"]
    t["_stop_dist_pct"] = abs(ep - sl) / ep * 100.0 if ep else 0.0
    t["_raw_rr"] = t.get("raw_rr", 0.0)
    t["_mtf_event"] = str(sp.get("mtf_structural_event", "")).replace("EventType.", "")
    t["_trig"] = sp.get("ltf_entry_reason", "")
    t["_kz"] = str(sp.get("mtf_keyzone_id", ""))
    t["_is_win"] = t["net_r"] > 0.05
    t["_is_be"] = abs(t["net_r"]) <= 0.05
    t["_is_stopout"] = "INITIAL_LTF_SL" in t.get("exit_reason", "")
    t["_is_trail"] = "TRAIL" in t.get("exit_reason", "")

# Print discriminators
print("\n" + "=" * 110)
print(f"{'Trade ID':<35} | {'Asset Set':<12} | {'Net R':<8} | {'Status':<7} | {'Align->Retest':<13} | {'Retest->Entry':<13} | {'SL %':<6} | {'Planned RR':<10} | {'MTF Event':<14} | {'KZ':<6}")
print("-" * 110)

for t in trades:
    cid = t["trade_id"].replace("cand_", "").split("_")[0] + "_" + t["symbol"].split("/")[0] + "_" + t["timeframe_set"]
    st = "WIN" if t["_is_win"] else ("BE" if t["_is_be"] else ("STOPOUT" if t["_is_stopout"] else "TRAIL"))
    kz = "OB" if "OB" in t["_kz"] else ("FVG" if "FVG" in t["_kz"] else "SYNTH")
    print(f"{t['trade_id']:<35} | {t['symbol'].split('/')[0]+' '+t['timeframe_set']:<12} | {t['net_r']:+7.4f}R | {st:<7} | {t['_align_to_retest_hr']:5.1f} hours    | {t['_retest_to_entry_hr']:5.1f} hours    | {t['_stop_dist_pct']:4.2f}% | {t['_raw_rr']:6.2f}R    | {t['_mtf_event']:<14} | {kz:<6}")

print("=" * 110)
