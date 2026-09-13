import json
import numpy as np
from datetime import datetime, timezone
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

trades = c1["all_trades"]
losses = [(i, t) for i, t in enumerate(trades) if t.get("net_r", 0) < -0.001]
print(f"Loaded {len(losses)} losing trades under C1.\n")

forensic_records = []

# Cache candle series per symbol and timeframe
candle_cache = {}

def get_candles(symbol, tf):
    key = f"{symbol}_{tf}"
    if key not in candle_cache:
        end_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        c = WarehouseLoader.load_history(symbol, tf, limit=1_000_000, start_time_ms=None, end_time_ms=end_ms)
        candle_cache[key] = c
    return candle_cache[key]

for rank, (orig_idx, t) in enumerate(losses):
    meta = t.get("metadata", {})
    p = meta.get("structural_provenance", {})
    sym = t["symbol"]
    tf_set_id = t["timeframe_set"]
    tf_info = TimeframeAligner.get_set(tf_set_id)
    
    net_r = t["net_r"]
    mfe_r = t.get("mfe_r", 0.0)
    mae_r = t.get("mae_r", 0.0)
    exit_reason = t["exit_reason"]
    dur_sec = t.get("duration_sec", 0)
    direction = t["directional_permission"]
    is_long = direction == "PERMIT_LONG"
    entry_p = t["fill_entry_price"]
    init_sl = t["initial_stop_price"]
    target_p = t["target_price"]
    raw_rr = t.get("raw_rr", 0.0)
    risk_dist = abs(entry_p - init_sl)
    risk_pct = (risk_dist / entry_p) * 100.0
    
    entry_ts = t["entry_timestamp"]
    exit_ts = t["exit_timestamp"]
    
    # A. MFE Classification
    if mfe_r < 0.5:
        mfe_cat = "<0.5R"
    elif mfe_r < 1.0:
        mfe_cat = "0.5-1.0R"
    elif mfe_r < 1.5:
        mfe_cat = "1.0-1.5R"
    else:
        mfe_cat = ">=1.5R"
        
    # B. MFE Timing
    time_to_mfe = meta.get("time_to_mfe", 0)
    if dur_sec == 0 or time_to_mfe == 0:
        mfe_timing = "immediate (bar 0)"
    else:
        ratio = time_to_mfe / dur_sec
        if ratio <= 0.25:
            mfe_timing = f"early ({ratio:.1%})"
        elif ratio <= 0.75:
            mfe_timing = f"mid ({ratio:.1%})"
        else:
            mfe_timing = f"late ({ratio:.1%})"
            
    # C. MFE-to-Exit Behavior
    if exit_reason == "INITIAL_LTF_SL":
        if mfe_r < 0.2:
            exit_behavior = "immediate_invalidation (straight to SL)"
        elif mfe_r < 0.5:
            exit_behavior = "weak_blip_to_SL"
        elif mfe_r < 1.0:
            exit_behavior = "moderate_traction_then_full_reversal"
        else:
            exit_behavior = "deep_run_failed_to_milestone_reversal"
    elif exit_reason == "MTF_STRUCTURAL_TRAIL":
        if mfe_r >= 1.5:
            exit_behavior = "extended_run_trailed_scratch"
        elif mfe_r >= 0.5:
            exit_behavior = "moderate_run_trailed_stop"
        else:
            exit_behavior = "immediate_trail_tighten_scratch"
    else:
        exit_behavior = exit_reason
        
    # D. MTF Setup Quality
    mtf_event = p.get("mtf_structural_event", "UNKNOWN")
    mtf_kz_id = p.get("mtf_keyzone_id", "UNKNOWN")
    mtf_align_ts = p.get("mtf_alignment_timestamp", 0)
    mtf_kz_create_ts = p.get("mtf_kz_creation_timestamp", 0)
    mtf_retest_ts = p.get("mtf_retest_timestamp", 0)
    
    # Timing deltas
    align_to_retest_min = (mtf_retest_ts - mtf_align_ts) // 60 if mtf_retest_ts and mtf_align_ts else 0
    kz_to_retest_min = (mtf_retest_ts - mtf_kz_create_ts) // 60 if mtf_retest_ts and mtf_kz_create_ts else 0
    
    # Analyze MTF candles around alignment and retest
    mtf_candles = get_candles(sym, tf_info.mtf)
    mtf_ts_map = {c.timestamp: idx for idx, c in enumerate(mtf_candles)}
    
    # Retest bar details
    retest_bar_idx = mtf_ts_map.get(mtf_retest_ts)
    align_bar_idx = mtf_ts_map.get(mtf_align_ts)
    
    mtf_displacement_pct = 0.0
    if align_bar_idx is not None and align_bar_idx > 0:
        c_align = mtf_candles[align_bar_idx]
        body = abs(c_align.close - c_align.open)
        mtf_displacement_pct = (body / c_align.open) * 100.0
        
    # Tap count: count how many MTF bars touched the retest price zone between creation and entry
    tap_count = 1
    if retest_bar_idx is not None and align_bar_idx is not None:
        # Check intervening bars
        start_idx = min(align_bar_idx, retest_bar_idx)
        end_idx = max(align_bar_idx, retest_bar_idx)
        tap_count = (end_idx - start_idx) + 1
        
    # E. LTF Trigger
    ltf_candles = get_candles(sym, tf_info.ltf)
    ltf_ts_map = {c.timestamp: idx for idx, c in enumerate(ltf_candles)}
    ltf_conf_ts = p.get("ltf_confirmation_timestamp", 0)
    ltf_bar_idx = ltf_ts_map.get(ltf_conf_ts)
    
    ltf_disp_pct = 0.0
    ltf_body_ratio = 0.0
    sweep_detected = False
    if ltf_bar_idx is not None and ltf_bar_idx > 5:
        c_ltf = ltf_candles[ltf_bar_idx]
        body = abs(c_ltf.close - c_ltf.open)
        rng = c_ltf.high - c_ltf.low
        ltf_disp_pct = (body / c_ltf.open) * 100.0
        ltf_body_ratio = body / rng if rng > 0 else 0.0
        
        # Check prior 5 bars for local liquidity sweep
        prior_5 = ltf_candles[ltf_bar_idx-5:ltf_bar_idx]
        if is_long:
            prior_low = min(c.low for c in prior_5)
            # Did trigger bar or bar before sweep below prior low and close above?
            sweep_detected = c_ltf.low < prior_low and c_ltf.close > prior_low
        else:
            prior_high = max(c.high for c in prior_5)
            sweep_detected = c_ltf.high > prior_high and c_ltf.close < prior_high

    ltf_trigger_reason = p.get("ltf_entry_reason", "UNKNOWN")
    retest_to_entry_min = (entry_ts - mtf_retest_ts) // 60 if mtf_retest_ts else 0
    
    # F. HTF Context
    htf_kz_id = p.get("htf_keyzone_id", "UNKNOWN")
    htf_target_prov = p.get("htf_target_provenance", "UNKNOWN")
    htf_phase = p.get("htf_phase", "UNKNOWN")
    htf_macro_dir = p.get("htf_macro_direction", "UNKNOWN")
    
    # G. Regime
    trend_regime = t.get("trend_regime", "UNKNOWN")
    vol_regime = t.get("volatility_regime", "UNKNOWN")
    mkt_phase = t.get("market_phase", "UNKNOWN")
    
    rec = {
        "rank": rank,
        "orig_trade_idx": orig_idx,
        "trade_id": t["trade_id"],
        "symbol": sym,
        "tf_set": tf_set_id,
        "direction": direction,
        "entry_timestamp": entry_ts,
        "exit_timestamp": exit_ts,
        "duration_min": dur_sec // 60,
        "entry_p": entry_p,
        "init_sl": init_sl,
        "target_p": target_p,
        "net_r": net_r,
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "exit_reason": exit_reason,
        "risk_dist": risk_dist,
        "risk_pct": risk_pct,
        "raw_rr": raw_rr,
        "mfe_cat": mfe_cat,
        "mfe_timing": mfe_timing,
        "exit_behavior": exit_behavior,
        "mtf_event": mtf_event.replace("EventType.", ""),
        "mtf_kz_id": mtf_kz_id,
        "mtf_displacement_pct": round(mtf_displacement_pct, 2),
        "align_to_retest_min": align_to_retest_min,
        "kz_to_retest_min": kz_to_retest_min,
        "tap_count_bars": tap_count,
        "retest_to_entry_min": retest_to_entry_min,
        "ltf_trigger_reason": ltf_trigger_reason,
        "ltf_disp_pct": round(ltf_disp_pct, 2),
        "ltf_body_ratio": round(ltf_body_ratio, 2),
        "sweep_detected": sweep_detected,
        "htf_kz_id": htf_kz_id,
        "htf_target_prov": htf_target_prov,
        "htf_phase": htf_phase.replace("MarketPhase.", ""),
        "htf_macro_dir": htf_macro_dir,
        "trend_regime": trend_regime,
        "vol_regime": vol_regime,
        "mkt_phase": mkt_phase
    }
    forensic_records.append(rec)

print(f"Successfully processed all {len(forensic_records)} forensic records.")
with open("scratch/d0_forensic_records.json", "w") as f:
    json.dump(forensic_records, f, indent=2)
print("Saved to scratch/d0_forensic_records.json")
