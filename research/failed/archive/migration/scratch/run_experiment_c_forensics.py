import json
import os
from datetime import datetime, timezone

def analyze_h0_forensics():
    h0_path = "scratch/canonical_h0_backtest_dev.json"
    with open(h0_path) as f:
        h0_data = json.load(f)
    
    trades = h0_data.get("all_trades", [])
    print(f"Total H0 trades: {len(trades)}")
    
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    # 1. Per-trade metrics
    trade_metrics = []
    for i, t in enumerate(trades):
        entry_ts = t.get("entry_timestamp", 0)
        exit_ts = t.get("exit_timestamp", 0)
        mfe_r = t.get("mfe_r", 0.0)
        mae_r = t.get("mae_r", 0.0)
        realized_r = t.get("net_r", 0.0)
        exit_reason = t.get("exit_reason", "UNKNOWN")
        
        # Timing metadata
        meta = t.get("metadata", {})
        mfe_ts = meta.get("mfe_timestamp", exit_ts)
        time_to_mfe = mfe_ts - entry_ts if mfe_ts and entry_ts else 0
        time_mfe_to_exit = exit_ts - mfe_ts if exit_ts and mfe_ts else 0
        total_duration = exit_ts - entry_ts if exit_ts and entry_ts else 0
        
        retention = realized_r / mfe_r if mfe_r > 0 else 0.0
        
        trade_metrics.append({
            "trade_idx": i,
            "trade_id": t.get("trade_id"),
            "stream_id": t.get("stream_id"),
            "symbol": t.get("symbol"),
            "timeframe_set": t.get("timeframe_set"),
            "direction": t.get("directional_permission"),
            "entry_ts": entry_ts,
            "exit_ts": exit_ts,
            "entry_price": t.get("fill_entry_price", t.get("entry_price")),
            "initial_stop": t.get("initial_stop_price"),
            "current_stop": t.get("current_stop_price"),
            "target_price": t.get("target_price"),
            "planned_rr": t.get("raw_rr", 0.0),
            "mfe_r": mfe_r,
            "mae_r": mae_r,
            "realized_r": realized_r,
            "retention_ratio": retention,
            "exit_reason": exit_reason,
            "time_to_mfe_sec": time_to_mfe,
            "time_mfe_to_exit_sec": time_mfe_to_exit,
            "total_duration_sec": total_duration,
            "mfe_ts": mfe_ts
        })
        
    # 2. Threshold subsequent outcomes
    threshold_analysis = {}
    for th in thresholds:
        qual_trades = [tm for tm in trade_metrics if tm["mfe_r"] >= th]
        n_qual = len(qual_trades)
        
        remained_profitable = len([tm for tm in qual_trades if tm["realized_r"] > 0.05])
        returned_breakeven = len([tm for tm in qual_trades if -0.05 <= tm["realized_r"] <= 0.05])
        became_losses = len([tm for tm in qual_trades if tm["realized_r"] < -0.05])
        hit_target = len([tm for tm in qual_trades if tm["exit_reason"] == "HTF_TP"])
        mtf_trail_exit = len([tm for tm in qual_trades if tm["exit_reason"] == "MTF_STRUCTURAL_TRAIL"])
        initial_sl_exit = len([tm for tm in qual_trades if tm["exit_reason"] == "INITIAL_LTF_SL"])
        
        threshold_analysis[th] = {
            "n_qual": n_qual,
            "remained_profitable": remained_profitable,
            "returned_breakeven": returned_breakeven,
            "became_losses": became_losses,
            "hit_target": hit_target,
            "mtf_trail_exit": mtf_trail_exit,
            "initial_sl_exit": initial_sl_exit,
            "trades": [tm["trade_idx"] for tm in qual_trades]
        }
        
    # 3. Specifically isolate trades with MFE >= 2R and realized_R < 0 in H0
    mfe_loss_h0 = [tm for tm in trade_metrics if tm["mfe_r"] >= 2.0 and tm["realized_r"] < 0]
    
    # 4. Also load Treatment B (EXP_TARGET_STRUCTURAL_01) to cross-reference the 9 trades
    exp_b_path = "scratch/exp_target_structural_01_dev.json"
    exp_b_mfe_loss = []
    if os.path.exists(exp_b_path):
        with open(exp_b_path) as f:
            exp_b_data = json.load(f)
        exp_b_trades = exp_b_data.get("all_trades", [])
        for i, t in enumerate(exp_b_trades):
            mfe_r = t.get("mfe_r", 0.0)
            realized_r = t.get("net_r", 0.0)
            if mfe_r >= 2.0 and realized_r < 0:
                exp_b_mfe_loss.append({
                    "trade_idx": i,
                    "trade_id": t.get("trade_id"),
                    "stream_id": t.get("stream_id"),
                    "symbol": t.get("symbol"),
                    "direction": t.get("directional_permission"),
                    "entry_ts": t.get("entry_timestamp"),
                    "exit_ts": t.get("exit_timestamp"),
                    "entry_price": t.get("fill_entry_price", t.get("entry_price")),
                    "initial_stop": t.get("initial_stop_price"),
                    "target_price": t.get("target_price"),
                    "planned_rr": t.get("raw_rr"),
                    "mfe_r": mfe_r,
                    "mae_r": t.get("mae_r"),
                    "realized_r": realized_r,
                    "exit_reason": t.get("exit_reason")
                })
                
    output = {
        "trade_metrics": trade_metrics,
        "threshold_analysis": threshold_analysis,
        "h0_mfe_loss_trades": mfe_loss_h0,
        "exp_b_mfe_loss_trades": exp_b_mfe_loss
    }
    
    with open("scratch/h0_monetization_forensics_summary.json", "w") as f:
        json.dump(output, f, indent=2)
        
    print("Forensics summary saved to scratch/h0_monetization_forensics_summary.json")

if __name__ == "__main__":
    analyze_h0_forensics()
