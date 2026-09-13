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

candle_cache = {}

def get_candles(symbol, tf):
    key = f"{symbol}_{tf}"
    if key not in candle_cache:
        end_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        c = WarehouseLoader.load_history(symbol, tf, limit=1_000_000, start_time_ms=None, end_time_ms=end_ms)
        candle_cache[key] = c
    return candle_cache[key]

forensic_records = []

for rank, (orig_idx, t) in enumerate(losses):
    meta = t.get("metadata", {})
    p = meta.get("structural_provenance", {})
    sym = t["symbol"]
    tf_set_id = t["timeframe_set"]
    tf_info = TimeframeAligner.get_set(tf_set_id)
    
    direction = t["directional_permission"]
    is_long = direction == "PERMIT_LONG"
    entry_p = t["fill_entry_price"]
    init_sl = t["initial_stop_price"]
    target_p = t["target_price"]
    exit_p = t["exit_price"]
    net_r = t["net_r"]
    mfe_r = t.get("mfe_r", 0.0)
    mae_r = t.get("mae_r", 0.0)
    exit_reason = t["exit_reason"]
    dur_sec = t.get("duration_sec", 0)
    raw_rr = t.get("raw_rr", 0.0)
    risk_dist = abs(entry_p - init_sl)
    target_dist = abs(target_p - entry_p)
    risk_pct = (risk_dist / entry_p) * 100.0
    target_pct = (target_dist / entry_p) * 100.0
    
    entry_ts = t["entry_timestamp"]
    exit_ts = t["exit_timestamp"]
    time_to_mfe = meta.get("time_to_mfe", 0)
    time_mfe_to_exit = max(0, dur_sec - time_to_mfe)
    c1_active = meta.get("breakeven_triggered", False)
    
    # -------------------------------------------------------------------------
    # 1. HTF FORENSICS
    # -------------------------------------------------------------------------
    htf_dir = p.get("htf_macro_direction", "UNKNOWN")
    htf_event = p.get("htf_structural_event", "HTF_CONTINUATION_OR_REVERSAL")
    htf_phase = p.get("htf_phase", "UNKNOWN").replace("MarketPhase.", "")
    htf_kz = p.get("htf_keyzone_id", "UNKNOWN")
    htf_dest = p.get("htf_target_provenance", "UNKNOWN")
    htf_context_ts = p.get("htf_context_timestamp", 0)
    htf_interact_ts = p.get("htf_interaction_timestamp", 0)
    htf_kz_create_ts = p.get("htf_kz_creation_timestamp", 0)
    
    htf_candles = get_candles(sym, tf_info.htf)
    htf_ts_map = {c.timestamp: idx for idx, c in enumerate(htf_candles)}
    htf_idx = htf_ts_map.get(htf_context_ts)
    
    htf_ret_5bar = 0.0
    if htf_idx is not None and htf_idx >= 5:
        c_now = htf_candles[htf_idx]
        c_prev = htf_candles[htf_idx-5]
        htf_ret_5bar = (c_now.close - c_prev.close) / c_prev.close * 100.0
        
    htf_aligned_with_trend = (htf_ret_5bar > 0) if is_long else (htf_ret_5bar < 0)
    
    # -------------------------------------------------------------------------
    # 2. MTF FORENSICS
    # -------------------------------------------------------------------------
    mtf_event = p.get("mtf_structural_event", "UNKNOWN").replace("EventType.", "")
    mtf_kz_id = p.get("mtf_keyzone_id", "UNKNOWN")
    mtf_align_ts = p.get("mtf_alignment_timestamp", 0)
    mtf_kz_create_ts = p.get("mtf_kz_creation_timestamp", 0)
    mtf_retest_ts = p.get("mtf_retest_timestamp", 0)
    
    mtf_candles = get_candles(sym, tf_info.mtf)
    mtf_ts_map = {c.timestamp: idx for idx, c in enumerate(mtf_candles)}
    mtf_align_idx = mtf_ts_map.get(mtf_align_ts)
    mtf_retest_idx = mtf_ts_map.get(mtf_retest_ts)
    
    # MTF 10-bar return prior to alignment
    mtf_prior_ret = 0.0
    if mtf_align_idx is not None and mtf_align_idx >= 10:
        c_now = mtf_candles[mtf_align_idx]
        c_prev = mtf_candles[mtf_align_idx-10]
        mtf_prior_ret = (c_now.close - c_prev.close) / c_prev.close * 100.0
        
    # Prior MTF direction
    mtf_prev_dir = "BULLISH" if mtf_prior_ret > 0 else "BEARISH"
    is_counter_phase = (mtf_prev_dir != htf_dir)
    
    # MTF displacement on alignment
    mtf_disp_pct = 0.0
    if mtf_align_idx is not None:
        c_al = mtf_candles[mtf_align_idx]
        body = abs(c_al.close - c_al.open)
        mtf_disp_pct = (body / c_al.open) * 100.0
        
    # Retest timing & depth
    align_to_retest_sec = max(0, mtf_retest_ts - mtf_align_ts) if mtf_retest_ts and mtf_align_ts else 0
    align_to_retest_bars = 0
    if mtf_align_idx is not None and mtf_retest_idx is not None:
        align_to_retest_bars = max(0, mtf_retest_idx - mtf_align_idx)
        
    kz_age_sec = max(0, mtf_retest_ts - mtf_kz_create_ts) if mtf_retest_ts and mtf_kz_create_ts else 0
    
    # Intervening tests (tap count)
    intervening_bars = 1
    if mtf_align_idx is not None and mtf_retest_idx is not None:
        intervening_bars = max(1, mtf_retest_idx - mtf_align_idx + 1)
        
    # Retest penetration depth relative to retest candle
    retest_candle_depth_pct = 0.0
    if mtf_retest_idx is not None:
        c_ret = mtf_candles[mtf_retest_idx]
        c_rng = c_ret.high - c_ret.low
        if c_rng > 0:
            if is_long:
                # depth from open/high down to low
                retest_candle_depth_pct = (c_ret.high - c_ret.low) / c_ret.open * 100.0
            else:
                retest_candle_depth_pct = (c_ret.high - c_ret.low) / c_ret.open * 100.0
                
    # -------------------------------------------------------------------------
    # 3. LTF FORENSICS
    # -------------------------------------------------------------------------
    ltf_candles = get_candles(sym, tf_info.ltf)
    ltf_ts_map = {c.timestamp: idx for idx, c in enumerate(ltf_candles)}
    ltf_conf_ts = p.get("ltf_confirmation_timestamp", 0)
    ltf_idx = ltf_ts_map.get(ltf_conf_ts)
    
    ltf_trigger_reason = p.get("ltf_entry_reason", "UNKNOWN")
    has_sweep = "SWEEP" in ltf_trigger_reason
    has_disp = "DISPLACEMENT" in ltf_trigger_reason
    has_choch = "CHOCH" in ltf_trigger_reason or "BOS" in ltf_trigger_reason
    
    ltf_disp_pct = 0.0
    ltf_body_ratio = 0.0
    if ltf_idx is not None:
        c_ltf = ltf_candles[ltf_idx]
        b = abs(c_ltf.close - c_ltf.open)
        r = c_ltf.high - c_ltf.low
        ltf_disp_pct = (b / c_ltf.open) * 100.0
        ltf_body_ratio = (b / r) if r > 0 else 0.0
        
    # Distance from entry to initial SL
    dist_entry_to_sl_pct = risk_pct
    
    # -------------------------------------------------------------------------
    # 4. FAILURE CLASS ASSIGNMENT (A through I)
    # -------------------------------------------------------------------------
    assigned_classes = []
    
    # A. Immediate LTF failure: MFE < 0.2R and stops out rapidly
    if mfe_r < 0.20 and exit_reason == "INITIAL_LTF_SL":
        assigned_classes.append("A. Immediate LTF failure")
        
    # B. Weak early traction: 0.2R <= MFE < 0.5R
    if 0.20 <= mfe_r < 0.50 and exit_reason == "INITIAL_LTF_SL":
        assigned_classes.append("B. Weak early traction")
        
    # C. Moderate favorable excursion but <1.5R: 0.5R <= MFE < 1.5R, not protected by C1
    if 0.50 <= mfe_r < 1.50 and exit_reason == "INITIAL_LTF_SL":
        assigned_classes.append("C. Moderate favorable excursion but <1.5R")
        
    # D. C1-protected reversal: reached >=1.5R or protected by cost-covering stop
    if c1_active or (mfe_r >= 1.50 and "TRAIL" in exit_reason):
        assigned_classes.append("D. C1-protected reversal")
        
    # E. High-MFE failure: MFE >= 2.0R but failed to reach HTF target
    if mfe_r >= 2.00:
        assigned_classes.append("E. High-MFE failure")
        
    # F. MTF trailing failure: Trailed stop exited with loss
    if "TRAIL" in exit_reason and net_r < -0.001:
        assigned_classes.append("F. MTF trailing failure")
        
    # G. HTF destination failure: MFE was >= 3.0R but target was set excessively far (>8R)
    if mfe_r >= 3.00 and raw_rr >= 8.0:
        assigned_classes.append("G. HTF destination failure")
        
    # H. Structural/setup ambiguity: minor INTERNAL_CHOCH or weak MTF displacement (<2%)
    if mtf_event == "INTERNAL_CHOCH" or mtf_disp_pct < 2.0:
        assigned_classes.append("H. Structural/setup ambiguity")
        
    rec = {
        "rank": rank,
        "orig_trade_idx": orig_idx,
        "trade_id": t["trade_id"],
        "symbol": sym,
        "tf_set": tf_set_id,
        "direction": direction,
        "entry_ts": entry_ts,
        "exit_ts": exit_ts,
        "dur_min": dur_sec // 60,
        "entry_p": entry_p,
        "init_sl": init_sl,
        "target_p": target_p,
        "exit_p": exit_p,
        "net_r": net_r,
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "time_to_mfe_min": time_to_mfe // 60,
        "time_mfe_to_exit_min": time_mfe_to_exit // 60,
        "c1_active": c1_active,
        "exit_reason": exit_reason,
        "raw_rr": raw_rr,
        "risk_dist": risk_dist,
        "risk_pct": risk_pct,
        "target_dist": target_dist,
        "target_pct": target_pct,
        # HTF
        "htf_dir": htf_dir,
        "htf_event": htf_event,
        "htf_phase": htf_phase,
        "htf_kz": htf_kz,
        "htf_dest": htf_dest,
        "htf_ret_5bar": htf_ret_5bar,
        "htf_aligned_with_trend": htf_aligned_with_trend,
        # MTF
        "mtf_prev_dir": mtf_prev_dir,
        "is_counter_phase": is_counter_phase,
        "mtf_event": mtf_event,
        "mtf_kz_id": mtf_kz_id,
        "mtf_disp_pct": mtf_disp_pct,
        "align_to_retest_min": align_to_retest_sec // 60,
        "align_to_retest_bars": align_to_retest_bars,
        "kz_age_min": kz_age_sec // 60,
        "intervening_bars": intervening_bars,
        "retest_candle_depth_pct": retest_candle_depth_pct,
        # LTF
        "ltf_trigger_reason": ltf_trigger_reason,
        "has_sweep": has_sweep,
        "has_disp": has_disp,
        "has_choch": has_choch,
        "ltf_disp_pct": ltf_disp_pct,
        "ltf_body_ratio": ltf_body_ratio,
        # Assigned Failure Classes
        "assigned_classes": assigned_classes
    }
    forensic_records.append(rec)

print(f"Extracted {len(forensic_records)} deep forensic records.")
with open("scratch/deep_forensic_records.json", "w") as f:
    json.dump(forensic_records, f, indent=2)
print("Saved to scratch/deep_forensic_records.json")
