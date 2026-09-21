import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_intelligence.primitives import Candle
from market_data.data_manager import DataManager
from strategy_candidate.replayer import CandidateReplayer

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

def run_test():
    symbol = "BTC/USDT"
    set_name = "Set 3"
    tfs = ["1d", "4h", "1h"]
    
    print(f"Loading data for {symbol} {set_name}...")
    htf = load_candles(symbol, tfs[0])
    mtf = load_candles(symbol, tfs[1])
    ltf = load_candles(symbol, tfs[2])
    
    print(f"Loaded {len(htf)} HTF, {len(mtf)} MTF, {len(ltf)} LTF candles.")
    
    if len(ltf) < 100:
        print("Not enough data.")
        return
        
    replayer = CandidateReplayer()
    print("Running Long replay...")
    result_long = replayer.run(
        symbol=symbol,
        set_name=set_name,
        htf_candles=htf,
        mtf_candles=mtf,
        ltf_candles=ltf,
        starting_balance=1000.0,
        risk_pct=0.01,
        direction=1
    )
    
    print(f"Long Trades Executed: {len(result_long.trades)}")
    print(f"Final Balance (Long): {result_long.final_balance:.2f}")
    if result_long.trades:
        print("Sample Long Trade:")
        print(result_long.trades[0])
        
    print("\nRunning Short replay...")
    result_short = replayer.run(
        symbol=symbol,
        set_name=set_name,
        htf_candles=htf,
        mtf_candles=mtf,
        ltf_candles=ltf,
        starting_balance=1000.0,
        risk_pct=0.01,
        direction=-1
    )
    
    print(f"Short Trades Executed: {len(result_short.trades)}")
    print(f"Final Balance (Short): {result_short.final_balance:.2f}")
    if result_short.trades:
        print("Sample Short Trade:")
        print(result_short.trades[0])

if __name__ == "__main__":
    run_test()
