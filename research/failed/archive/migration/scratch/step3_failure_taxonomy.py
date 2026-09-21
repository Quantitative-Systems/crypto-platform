import json
import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

trades = d1["all_trades"]
stopouts = [t for t in trades if "INITIAL_LTF_SL" in t.get("exit_reason", "")]

print(f"Total Stop-Outs in D1: {len(stopouts)}")
print("=" * 100)

for i, t in enumerate(stopouts):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    entry_ts = t["entry_timestamp"]
    exit_ts = t["exit_timestamp"]
    net_r = t["net_r"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    ep = t["entry_price"]
    sl = t["initial_stop_price"]
    tp = t["target_price"]
    rr = t["raw_rr"]
    dur_min = (exit_ts - entry_ts) / 60.0 if (exit_ts and entry_ts) else 0.0
    
    sp = t.get("metadata", {}).get("structural_provenance", {})
    trig = sp.get("ltf_entry_reason")
    mtf_event = sp.get("mtf_structural_event")
    htf_phase = sp.get("htf_phase")
    mtf_kz = sp.get("mtf_keyzone_id")
    align_ts = sp.get("mtf_alignment_timestamp")
    retest_ts = sp.get("mtf_retest_timestamp")
    conf_ts = sp.get("ltf_confirmation_timestamp")
    
    align_to_retest_hr = (retest_ts - align_ts) / 3600.0 if (retest_ts and align_ts) else 0.0
    retest_to_entry_hr = (conf_ts - retest_ts) / 3600.0 if (conf_ts and retest_ts) else 0.0
    
    stop_dist_pct = abs(ep - sl) / ep * 100.0 if ep else 0.0
    
    print(f"[{i+1:02d}] {cid}")
    print(f"     Asset/Set/Dir:   {sym} | {st} | {dir_}")
    print(f"     Timestamps:      Align={align_ts} | Retest={retest_ts} | Entry={entry_ts} | Exit={exit_ts}")
    print(f"     Latencies:       Align->Retest: {align_to_retest_hr:.1f}h | Retest->Entry: {retest_to_entry_hr:.1f}h | Trade Duration: {dur_min:.0f}m")
    print(f"     Geometry:        Entry={ep} | SL={sl} ({stop_dist_pct:.2f}%) | TP={tp} | Planned RR={rr:.2f}R")
    print(f"     Outcome:         Net R={net_r:+.4f}R | MFE={mfe:.2f}R | MAE={mae:.2f}R | Exit={t['exit_reason']}")
    print(f"     Structure:       HTF Phase={htf_phase} | MTF Shift={mtf_event} | MTF KZ={mtf_kz} | Trig={trig}")
    print("-" * 100)
