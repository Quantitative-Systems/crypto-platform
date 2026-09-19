import os
import sys
import json
import csv
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_intelligence.primitives import Candle
from market_data.data_manager import DataManager, ALL_ASSETS
from strategy_candidate.replayer import CandidateReplayer

SETS = {
    "Set 1": ["1M", "1w", "1d"],
    "Set 2": ["1w", "1d", "4h"],
    "Set 3": ["1d", "4h", "1h"],
    "Set 4": ["4h", "1h", "15m"],
    "Set 5": ["1h", "15m", "5m"],
    "Set 6": ["15m", "5m", "1m"],
}

def load_candles(symbol: str, tf: str):
    fpath = DataManager.get_cache_filepath(symbol, tf)
    if not os.path.exists(fpath):
        clean_sym = symbol.replace("/", "").upper()
        alt = os.path.join(os.path.dirname(fpath), f"binance_{clean_sym}_{tf}.json")
        if os.path.exists(alt):
            fpath = alt
    if not os.path.exists(fpath):
        return []
        
    with open(fpath, "r") as f:
        raw = json.load(f)
        
    candles = []
    for r in raw:
        candles.append(Candle(
            timestamp=int(r[0]),
            open=float(r[1]),
            high=float(r[2]),
            low=float(r[3]),
            close=float(r[4]),
            volume=float(r[5])
        ))
    return candles

def calculate_metrics(trades, start_balance):
    if not trades:
        return 0, 0, 0, 0.0, 0.0
        
    balance = start_balance
    peak = balance
    max_dd = 0.0
    wins = 0
    total_pnl = 0.0
    
    for t in trades:
        pnl = t["pnl"]
        balance += pnl
        total_pnl += pnl
        
        if balance > peak:
            peak = balance
            
        dd = (peak - balance) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            
        if pnl > 0:
            wins += 1
            
    win_rate = (wins / len(trades)) * 100
    max_dd_pct = max_dd * 100
    
    return len(trades), wins, win_rate, total_pnl, max_dd_pct

def main():
    print("Starting Full Backtest (Test D)...")
    replayer = CandidateReplayer()
    
    all_trades = []
    results = []
    
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        for set_name, tfs in SETS.items():
            print(f"Processing {symbol} {set_name}...")
            htf = load_candles(symbol, tfs[0])
            mtf = load_candles(symbol, tfs[1])
            ltf = load_candles(symbol, tfs[2])
            
            if len(htf) < 50 or len(mtf) < 50 or len(ltf) < 50:
                print(f"Skipping {symbol} {set_name} due to insufficient data.")
                continue
                
            # Long
            res_long = replayer.run(symbol, set_name, htf, mtf, ltf, direction=1)
            all_trades.extend(res_long.trades)
            num, wins, wr, pnl, dd = calculate_metrics(res_long.trades, 1000.0)
            results.append({
                "Asset": asset,
                "Set": set_name,
                "Direction": "LONG",
                "Trades": num,
                "WinRate": wr,
                "NetPnL": pnl,
                "MaxDD": dd,
                "FinalBalance": res_long.final_balance
            })
            
            # Short
            res_short = replayer.run(symbol, set_name, htf, mtf, ltf, direction=-1)
            all_trades.extend(res_short.trades)
            num, wins, wr, pnl, dd = calculate_metrics(res_short.trades, 1000.0)
            results.append({
                "Asset": asset,
                "Set": set_name,
                "Direction": "SHORT",
                "Trades": num,
                "WinRate": wr,
                "NetPnL": pnl,
                "MaxDD": dd,
                "FinalBalance": res_short.final_balance
            })

    # Save ledger
    os.makedirs("strategy_candidate/results", exist_ok=True)
    with open("strategy_candidate/results/trade_ledger.csv", "w", newline='') as f:
        if all_trades:
            writer = csv.DictWriter(f, fieldnames=all_trades[0].keys())
            writer.writeheader()
            writer.writerows(all_trades)
            
    # Save summary
    with open("strategy_candidate/results/summary.csv", "w", newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            
    print("Full Backtest Complete!")
    print(f"Total Trades Generated: {len(all_trades)}")
    
if __name__ == "__main__":
    main()
