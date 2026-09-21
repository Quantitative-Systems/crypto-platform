import json
import numpy as np

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

trades = d1["all_trades"]

print(f"Analyzing all 24 executed trades in D1...")
print("=" * 100)

for t in trades:
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    net_r = t["net_r"]
    exit_r = t["exit_reason"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    
    sp = t.get("metadata", {}).get("structural_provenance", {})
    trig = sp.get("ltf_entry_reason", "")
    mtf_event = str(sp.get("mtf_structural_event", "")).replace("EventType.", "")
    htf_phase = str(sp.get("htf_phase", "")).replace("MarketPhase.", "")
    mtf_kz = str(sp.get("mtf_keyzone_id", ""))
    align_ts = sp.get("mtf_alignment_timestamp", 0)
    retest_ts = sp.get("mtf_retest_timestamp", 0)
    conf_ts = sp.get("ltf_confirmation_timestamp", 0)
    
    align_to_retest_hr = (retest_ts - align_ts) / 3600.0 if (retest_ts and align_ts) else 0.0
    retest_to_entry_hr = (conf_ts - retest_ts) / 3600.0 if (conf_ts and retest_ts) else 0.0
    
    kz_type = "FVG" if "FVG" in mtf_kz else ("OB" if "OB" in mtf_kz else "SYNTH")
    archetype = "SWEEP" if "SWEEP" in trig else "DISP"
    
    is_win = net_r > 0.05
    is_be = abs(net_r) <= 0.05
    is_loss = net_r < -0.05
    is_stopout = "INITIAL_LTF_SL" in exit_r
    
    status = "WIN" if is_win else ("BE" if is_be else ("STOPOUT" if is_stopout else "TRAIL"))
    
    t["_parsed"] = {
        "status": status,
        "archetype": archetype,
        "kz_type": kz_type,
        "align_to_retest_hr": align_to_retest_hr,
        "retest_to_entry_hr": retest_to_entry_hr,
        "is_fast_retest": align_to_retest_hr <= 12.0,
        "is_fast_reaction": retest_to_entry_hr <= 4.0,
        "mtf_event": mtf_event,
        "htf_phase": htf_phase
    }

# Print summary table
print(f"{'Status':<8} | {'N':<3} | {'Fast Retest (<=12h)':<20} | {'Fast Reaction (<=4h)':<20} | {'Sweep Archetype':<16} | {'OB Zone':<10} | {'FVG Zone':<10}")
print("-" * 100)

for st in ["WIN", "BE", "TRAIL", "STOPOUT"]:
    sub = [t["_parsed"] for t in trades if t["_parsed"]["status"] == st]
    n = len(sub)
    fast_ret = sum(1 for x in sub if x["is_fast_retest"])
    fast_react = sum(1 for x in sub if x["is_fast_reaction"])
    sweep = sum(1 for x in sub if x["archetype"] == "SWEEP")
    ob = sum(1 for x in sub if x["kz_type"] == "OB")
    fvg = sum(1 for x in sub if x["kz_type"] == "FVG")
    print(f"{st:<8} | {n:<3} | {fast_ret:2d} ({fast_ret/n*100:4.1f}%)          | {fast_react:2d} ({fast_react/n*100:4.1f}%)           | {sweep:2d} ({sweep/n*100:4.1f}%)        | {ob:2d} ({ob/n*100:4.1f}%)  | {fvg:2d} ({fvg/n*100:4.1f}%)")

print("=" * 100)
