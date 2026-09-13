import json
import sys
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, "/home/mrcn2/crypto-platform")
from market_data.warehouse_loader import WarehouseLoader

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

# Load candle cache for all 15 streams
candle_cache = {}
symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
tf_map = {
    "SET_1": "1d",
    "SET_2": "4h",
    "SET_3": "1h",
    "SET_4": "15m"
}

end_time_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
start_time_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

print("Loading raw candle data...")
for sym in symbols:
    for st, ltf_tf in tf_map.items():
        key = (sym, st)
        candles = WarehouseLoader.load_history(sym, ltf_tf, limit=1_000_000, start_time_ms=start_time_ms, end_time_ms=end_time_ms)
        candle_cache[key] = candles
        print(f"Loaded {len(candles)} candles for {sym} {st} ({ltf_tf})")

print("Candle loading complete.\n")

# Collect all candidates reaching RISK_GATE
risk_gate_cands = []
for sr in d1["stream_results"]:
    sym = sr["asset"] + "/USDT"
    st = sr["timeframe_set"]
    if st == "SET_5":
        continue
    for c in sr.get("all_candidates", []):
        stages = c.get("stages_reached", [])
        ep = c.get("ltf_entry_price")
        sl = c.get("ltf_structural_sl")
        tp = c.get("htf_target_price")
        ts = c.get("ltf_confirmation_timestamp")
        
        if "RISK_GATE" in stages and ep and sl and tp and ts and ep != sl:
            dir_ = c.get("mtf_setup_direction") or c.get("htf_macro_direction")
            is_long = "LONG" in str(dir_).upper() or "BULLISH" in str(dir_).upper()
            
            # Risk and planned RR
            risk_dist = abs(ep - sl)
            reward_dist = abs(tp - ep)
            # Check directionality
            valid_geom = (tp > ep if is_long else tp < ep) and (sl < ep if is_long else sl > ep)
            raw_rr = reward_dist / risk_dist if risk_dist > 0 else 0.0
            
            risk_gate_cands.append({
                "candidate_id": c.get("candidate_id"),
                "symbol": sym,
                "timeframe_set": st,
                "direction": "LONG" if is_long else "SHORT",
                "entry_price": ep,
                "stop_price": sl,
                "target_price": tp,
                "confirmation_ts": ts,
                "state": c.get("state"),
                "invalidation_reason": c.get("invalidation_reason") or "ENTERED/PASSED",
                "raw_rr": raw_rr,
                "valid_geom": valid_geom,
                "mtf_event": str(c.get("mtf_structural_event")),
                "mtf_keyzone": c.get("mtf_keyzone_id"),
                "htf_keyzone": c.get("htf_keyzone_id"),
                "htf_target_prov": c.get("htf_target_provenance"),
                "htf_phase": str(c.get("htf_phase")),
                "mtf_align_ts": c.get("mtf_alignment_timestamp") or 0,
                "mtf_retest_ts": c.get("mtf_retest_timestamp") or 0,
                "ltf_entry_reason": c.get("ltf_entry_reason") or ""
            })

print(f"Total valid candidates reaching RISK_GATE with pricing geometry: {len(risk_gate_cands)}")

# Forward simulation for each candidate
def simulate_forward(cand, candles):
    ep = cand["entry_price"]
    sl = cand["stop_price"]
    tp = cand["target_price"]
    ts = cand["confirmation_ts"]
    is_long = cand["direction"] == "LONG"
    risk = abs(ep - sl)
    
    if risk <= 0:
        return None
        
    # Find start candle
    start_idx = -1
    for i, c in enumerate(candles):
        if c.timestamp >= ts:
            start_idx = i
            break
            
    if start_idx == -1 or start_idx >= len(candles):
        return None
        
    mfe_price = ep
    mae_price = ep
    mfe_ts = ts
    mae_ts = ts
    outcome = "ACTIVE"
    exit_ts = ts
    
    # Iterate subsequent candles
    for c in candles[start_idx:]:
        # ADVERSE_FIRST check on bar extremes
        if is_long:
            # Check adverse first
            if c.low < mae_price:
                mae_price = c.low
                mae_ts = c.timestamp
            if c.high > mfe_price:
                mfe_price = c.high
                mfe_ts = c.timestamp
                
            # Check exit
            if c.low <= sl:
                outcome = "STOP_LOSS"
                exit_ts = c.timestamp
                break
            elif c.high >= tp:
                outcome = "TARGET"
                exit_ts = c.timestamp
                break
        else:
            # Short
            if c.high > mae_price:
                mae_price = c.high
                mae_ts = c.timestamp
            if c.low < mfe_price:
                mfe_price = c.low
                mfe_ts = c.timestamp
                
            if c.high >= sl:
                outcome = "STOP_LOSS"
                exit_ts = c.timestamp
                break
            elif c.low <= tp:
                outcome = "TARGET"
                exit_ts = c.timestamp
                break
                
    mfe_r = abs(mfe_price - ep) / risk
    mae_r = abs(mae_price - ep) / risk
    time_to_mfe_hr = (mfe_ts - ts) / 3600.0
    time_to_mae_hr = (mae_ts - ts) / 3600.0
    dur_hr = (exit_ts - ts) / 3600.0
    
    return {
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "mfe_05": mfe_r >= 0.5,
        "mfe_10": mfe_r >= 1.0,
        "mfe_15": mfe_r >= 1.5,
        "mfe_20": mfe_r >= 2.0,
        "mfe_40": mfe_r >= 4.0,
        "hit_target": outcome == "TARGET",
        "hit_stop": outcome == "STOP_LOSS",
        "time_to_mfe_hr": time_to_mfe_hr,
        "time_to_mae_hr": time_to_mae_hr,
        "duration_hr": dur_hr,
        "outcome": outcome
    }

results = []
for cand in risk_gate_cands:
    key = (cand["symbol"], cand["timeframe_set"])
    candles = candle_cache.get(key, [])
    sim = simulate_forward(cand, candles)
    if sim:
        res = dict(cand)
        res.update(sim)
        results.append(res)

print(f"Successfully simulated {len(results)} candidates forward.\n")

with open("scratch/adu01_counterfactual_sim_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Saved to scratch/adu01_counterfactual_sim_results.json")
