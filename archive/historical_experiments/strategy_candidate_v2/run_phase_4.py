import os
import csv
from run_backtest import ASSETS, TIMEFRAME_SETS, load_candles, run_single_set

def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_phase4")
    os.makedirs(output_dir, exist_ok=True)
    
    symbol = "BTC/USDT"
    set_name = "Set 4"
    sc = TIMEFRAME_SETS[set_name]
    
    print(f"Running Phase 4 Single Stream: {symbol} {set_name} ({sc['style']})")
    
    htf = load_candles(symbol, sc["HTF"])
    mtf = load_candles(symbol, sc["MTF"])
    ltf = load_candles(symbol, sc["LTF"])
    
    if htf is None or mtf is None or ltf is None:
        print("Missing data! Cannot run.")
        return
        
    result = run_single_set(symbol, set_name, htf, mtf, ltf)
    
    print(f"Trades: {result['total_trades']}, Balance: ${result['final_balance']:.2f}, Rejected6R: {result['rejected_6r']}")
    
    ledger_path = os.path.join(output_dir, "trade_ledger_phase4.csv")
    with open(ledger_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trade_id","symbol","set","direction","entry_ts","entry_price","fill_entry",
                     "size","entry_fee","initial_sl","tp1","tp2","tp3","planned_rr",
                     "exit_ts","exit_price","fill_exit","exit_reason","exit_fee","net_pnl","trailing_phase"])
        for t in result["trades"]:
            w.writerow([t["trade_id"],t["symbol"],t["set"],t["direction"],t["entry_ts"],
                       t["entry_price"],t["fill_entry"],t["size"],t["entry_fee"],
                       t["initial_sl"],t["tp1"],t["tp2"],t["tp3"],t["planned_rr"],
                       t["exit_ts"],t["exit_price"],t["fill_exit"],t["exit_reason"],
                       t["exit_fee"],t["net_pnl"],t["trailing_phase"]])
    
    print(f"Saved ledger to {ledger_path}")

if __name__ == "__main__":
    main()
