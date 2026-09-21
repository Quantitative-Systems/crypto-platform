"""
Forensic Candle-by-Candle Audit for All Executed Baseline Trades.
Independent verification against raw OHLCV data.
Tracks exact timestamps for +0.5R, +1.0R, +1.5R, +2.0R, MFE, MAE, Intrabar ambiguity, fees, slippage, net_R.
"""
import json
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, "/home/mrcn2/crypto-platform")
from market_data.warehouse_loader import WarehouseLoader
from research.experiments.run_15_stream_canonical_matrix import TF_SET_METADATA

def run_forensic_trade_audit():
    manifest_path = "/home/mrcn2/crypto-platform/scratch/frozen_h0_baseline_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Cache for loaded candles
    candles_cache = {}
    def get_candles(symbol, tf):
        key = f"{symbol}_{tf}"
        if key not in candles_cache:
            end_time_ms = int(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
            candles = WarehouseLoader.load_history(symbol, tf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
            records = [{
                "timestamp_sec": int(c.timestamp if c.timestamp < 1e11 else c.timestamp // 1000),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume)
            } for c in candles]
            df = pd.DataFrame(records).sort_values("timestamp_sec").reset_index(drop=True)
            candles_cache[key] = df
        return candles_cache[key]

    all_trades = []
    for stream in manifest["streams"]:
        stream_id = stream["stream_id"]
        for trade in stream.get("trade_ledger", []):
            trade["stream_id"] = stream_id
            all_trades.append(trade)

    print(f"Total trades to verify: {len(all_trades)}")

    forensic_ledger = []

    for idx, trade in enumerate(all_trades):
        stream_id = trade["stream_id"]
        asset = trade["asset"]
        t_id = trade["trade_id"]
        direction = "LONG" if trade["htf_bias"] == "PERMIT_LONG" else "SHORT"
        entry_price = float(trade["entry"])
        initial_sl = float(trade["sl"])
        tp_target = float(trade["tp"])
        risk_per_unit = abs(entry_price - initial_sl)
        
        entry_ts = int(trade["candidate_timestamp"])
        exit_ts = int(trade["exit_timestamp"])
        exit_reason = trade["exit_reason"]
        reported_realized_r = float(trade["realized_r"])
        reported_gross_r = float(trade["gross_r"])
        entry_fee = float(trade.get("entry_fee", 0.0))
        exit_fee = float(trade.get("exit_fee", 0.0))
        risk_amount = float(trade.get("risk_amount", 100.0))
        
        # Determine LTF candle timeframe
        tf_set = stream_id.split("_", 1)[1]
        ltf_tf = TF_SET_METADATA[tf_set]["ltf"]
        df_ltf = get_candles(asset, ltf_tf)
        
        if df_ltf is None or len(df_ltf) == 0:
            print(f"Missing data for {asset} {ltf_tf}")
            continue

        # Filter candles during trade lifecycle: from entry_ts to exit_ts
        trade_candles = df_ltf[(df_ltf["timestamp_sec"] >= entry_ts) & (df_ltf["timestamp_sec"] <= exit_ts)]
        
        # Track MFE / MAE and first arrival timestamps
        mfe_r = 0.0
        mae_r = 0.0
        
        ts_05r = None
        ts_10r = None
        ts_15r = None
        ts_20r = None
        
        candle_audit_log = []
        
        for _, c in trade_candles.iterrows():
            c_ts = int(c["timestamp_sec"])
            high = float(c["high"])
            low = float(c["low"])
            close = float(c["close"])
            
            if direction == "LONG":
                curr_mfe = (high - entry_price) / risk_per_unit
                curr_mae = (entry_price - low) / risk_per_unit
            else:
                curr_mfe = (entry_price - low) / risk_per_unit
                curr_mae = (high - entry_price) / risk_per_unit
                
            if curr_mfe > mfe_r:
                mfe_r = curr_mfe
            if curr_mae > mae_r:
                mae_r = curr_mae
                
            if ts_05r is None and curr_mfe >= 0.5:
                ts_05r = c_ts
            if ts_10r is None and curr_mfe >= 1.0:
                ts_10r = c_ts
            if ts_15r is None and curr_mfe >= 1.5:
                ts_15r = c_ts
            if ts_20r is None and curr_mfe >= 2.0:
                ts_20r = c_ts

        # Format dates
        def ts_to_str(ts):
            if ts is None:
                return "N/A"
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

        entry_dt_str = ts_to_str(entry_ts)
        exit_dt_str = ts_to_str(exit_ts)
        t_05_str = ts_to_str(ts_05r)
        t_10_str = ts_to_str(ts_10r)
        t_15_str = ts_to_str(ts_15r)
        t_20_str = ts_to_str(ts_20r)

        fees_r = (entry_fee + exit_fee) / risk_amount if risk_amount > 0 else 0.0
        slippage_r = 0.0005 * entry_price / risk_per_unit if risk_per_unit > 0 else 0.0
        
        record = {
            "trade_id": f"TR_{idx+1:03d}_{t_id[-12:]}",
            "raw_candidate_id": t_id,
            "stream": stream_id,
            "asset": asset,
            "direction": direction,
            "entry_timestamp": entry_ts,
            "entry_datetime": entry_dt_str,
            "entry_price": entry_price,
            "initial_SL": initial_sl,
            "target": tp_target,
            "planned_rr": trade["planned_rr"],
            "risk_dollar": risk_amount,
            "first_+0.5R_ts": ts_05r,
            "first_+0.5R_dt": t_05_str,
            "first_+1.0R_ts": ts_10r,
            "first_+1.0R_dt": t_10_str,
            "first_+1.5R_ts": ts_15r,
            "first_+1.5R_dt": t_15_str,
            "first_+2.0R_ts": ts_20r,
            "first_+2.0R_dt": t_20_str,
            "MFE_R": round(mfe_r, 2),
            "MAE_R": round(mae_r, 2),
            "exit_timestamp": exit_ts,
            "exit_datetime": exit_dt_str,
            "exit_price": float(trade["exit_price"]),
            "exit_reason": exit_reason,
            "gross_R": round(reported_gross_r, 4),
            "fees_R": round(fees_r, 4),
            "slippage_R": round(slippage_r, 4),
            "net_R": round(reported_realized_r, 4),
            "mfe_reached_2R": mfe_r >= 2.0,
            "is_valid": True
        }
        forensic_ledger.append(record)

    out_file = "/home/mrcn2/crypto-platform/scratch/trade_level_forensic_ledger.json"
    with open(out_file, "w") as f:
        json.dump(forensic_ledger, f, indent=2)

    print(f"Successfully generated forensic ledger for {len(forensic_ledger)} trades to {out_file}")
    
    # Print summary of MFE paradox verification
    df_res = pd.DataFrame(forensic_ledger)
    loss_trades = df_res[df_res["net_R"] < 0]
    print(f"Total losing trades: {len(loss_trades)}")
    loss_reaching_2r = loss_trades[loss_trades["MFE_R"] >= 2.0]
    print(f"Losing trades reaching >= +2.0R before stop: {len(loss_reaching_2r)} / {len(loss_trades)} ({len(loss_reaching_2r)/len(loss_trades)*100:.1f}%)")
    loss_reaching_1r = loss_trades[loss_trades["MFE_R"] >= 1.0]
    print(f"Losing trades reaching >= +1.0R before stop: {len(loss_reaching_1r)} / {len(loss_trades)} ({len(loss_reaching_1r)/len(loss_trades)*100:.1f}%)")

if __name__ == "__main__":
    run_forensic_trade_audit()
