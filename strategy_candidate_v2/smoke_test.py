import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_candidate_v2.run_backtest import run_single_set
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles

def run_smoke_test():
    symbol = "BTC/USDT"
    set_name = "Set 1"
    print(f"--- SMOKE TEST: {symbol} {set_name} ---")
    
    sc = TIMEFRAME_SETS[set_name]
    print("Loading data...")
    htf = load_candles(symbol, sc["HTF"])
    mtf = load_candles(symbol, sc["MTF"])
    ltf = load_candles(symbol, sc["LTF"])
    
    if not htf or not mtf or not ltf:
        print("FAIL: Missing data.")
        return
        
    print(f"Data loaded: HTF={len(htf)}, MTF={len(mtf)}, LTF={len(ltf)}")
    print("Running backtest...")
    
    result = run_single_set(symbol, set_name, htf, mtf, ltf)
    
    print("\n--- SMOKE TEST RESULTS ---")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Valid Setups (pre-6R): {result['valid_setups']}")
    print(f"Rejected by 6R: {result['rejected_6r']}")
    print(f"Final Balance: ${result['final_balance']:.2f}")

if __name__ == '__main__':
    run_smoke_test()
