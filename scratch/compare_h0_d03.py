import json
import sys

def load_results(path):
    with open(path, 'r') as f:
        return json.load(f)

def get_trades(results):
    trades = results.get("trade_ledger", [])
    # Re-calculate correct aggregate from raw ledger because of the realized_r vs realized_rr bug
    for t in trades:
        t["net_r_fixed"] = t.get("net_r", 0.0) # We know net_r is correctly populated in the trade objects
    return trades

def build_trade_map(trades):
    tmap = {}
    for t in trades:
        # Use a combination of stream, candidate, and entry timestamp to uniquely identify an execution
        # even if the candidate setup was executed multiple times
        key = (t["stream_id"], t["symbol"], t["candidate_timestamp"], t["entry_timestamp"])
        tmap[key] = t
    return tmap

def main():
    h0_path = "scratch/h0_dev_control_results.json"
    d03_path = "scratch/h_d03_dev_results.json"

    try:
        h0_res = load_results(h0_path)
        d03_res = load_results(d03_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)

    h0_trades = get_trades(h0_res)
    d03_trades = get_trades(d03_res)

    print("=== POPULATION EQUIVALENCE ===")
    print(f"H0 Total Trades: {len(h0_trades)}")
    print(f"D-03 Total Trades: {len(d03_trades)}")

    h0_map = build_trade_map(h0_trades)
    d03_map = build_trade_map(d03_trades)

    h0_keys = set(h0_map.keys())
    d03_keys = set(d03_map.keys())

    if h0_keys != d03_keys:
        print("❌ STOP: Setup population mismatch!")
        print(f"Keys only in H0: {len(h0_keys - d03_keys)}")
        print(f"Keys only in D-03: {len(d03_keys - h0_keys)}")
        sys.exit(1)
    else:
        print("✅ Setup populations match exactly.")

    # Calculate aggregates for H0
    h0_net_r = sum(t["net_r_fixed"] for t in h0_trades)
    h0_wins = [t for t in h0_trades if t["net_r_fixed"] > 0]
    h0_losses = [t for t in h0_trades if t["net_r_fixed"] <= 0]
    h0_gross_win = sum(t["net_r_fixed"] for t in h0_wins)
    h0_gross_loss = abs(sum(t["net_r_fixed"] for t in h0_losses))
    h0_pf = h0_gross_win / h0_gross_loss if h0_gross_loss > 0 else 0
    h0_wr = len(h0_wins) / len(h0_trades) if h0_trades else 0
    h0_exp = h0_net_r / len(h0_trades) if h0_trades else 0
    
    h0_initial_sl_count = sum(1 for t in h0_trades if t.get("exit_reason") == "INITIAL_LTF_SL")
    h0_tp_count = sum(1 for t in h0_trades if t.get("exit_reason") == "HTF_TP")
    h0_pl_count = sum(1 for t in h0_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL")
    
    # Calculate aggregates for D03
    d03_net_r = sum(t["net_r_fixed"] for t in d03_trades)
    d03_wins = [t for t in d03_trades if t["net_r_fixed"] > 0]
    d03_losses = [t for t in d03_trades if t["net_r_fixed"] <= 0]
    d03_gross_win = sum(t["net_r_fixed"] for t in d03_wins)
    d03_gross_loss = abs(sum(t["net_r_fixed"] for t in d03_losses))
    d03_pf = d03_gross_win / d03_gross_loss if d03_gross_loss > 0 else 0
    d03_wr = len(d03_wins) / len(d03_trades) if d03_trades else 0
    d03_exp = d03_net_r / len(d03_trades) if d03_trades else 0
    
    d03_initial_sl_count = sum(1 for t in d03_trades if t.get("exit_reason") == "INITIAL_LTF_SL")
    d03_tp_count = sum(1 for t in d03_trades if t.get("exit_reason") == "HTF_TP")
    d03_pl_count = sum(1 for t in d03_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL")

    print("\n=== PAIRED COMPARISON TABLE ===")
    print(f"| Metric            | H0 | D-03 | Delta |")
    print(f"| ----------------- | -: | ---: | ----: |")
    print(f"| Trades            | {len(h0_trades)} | {len(d03_trades)} | {len(d03_trades) - len(h0_trades)} |")
    print(f"| Win Rate          | {h0_wr*100:.1f}% | {d03_wr*100:.1f}% | {(d03_wr - h0_wr)*100:.1f}pp |")
    print(f"| Net R             | {h0_net_r:.2f} | {d03_net_r:.2f} | {d03_net_r - h0_net_r:.2f} |")
    print(f"| Expectancy        | {h0_exp:.2f} | {d03_exp:.2f} | {d03_exp - h0_exp:.2f} |")
    print(f"| Profit Factor     | {h0_pf:.2f} | {d03_pf:.2f} | {d03_pf - h0_pf:.2f} |")
    print(f"| Target Exits      | {h0_tp_count} | {d03_tp_count} | {d03_tp_count - h0_tp_count} |")
    print(f"| Initial SL Exits  | {h0_initial_sl_count} | {d03_initial_sl_count} | {d03_initial_sl_count - h0_initial_sl_count} |")
    print(f"| Profit-Lock Exits | {h0_pl_count} | {d03_pl_count} | {d03_pl_count - h0_pl_count} |")

    print("\n=== FORENSIC INVESTIGATION OF 22 D-03 PROFIT-LOCK EXITS ===")
    d03_pl_trades = [t for t in d03_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL"]
    for t in d03_pl_trades:
        key = (t["stream_id"], t["symbol"], t["candidate_timestamp"], t["entry_timestamp"])
        h0_t = h0_map[key]
        delta = t["net_r_fixed"] - h0_t["net_r_fixed"]
        classif = ""
        if delta > 0.05:
            classif = "PROTECTED CAPITAL"
        elif delta < -0.05:
            classif = "CHOKED RUNNER"
        else:
            classif = "NEUTRAL"
            
        print(f"Setup {t['trade_id']} ({t['stream_id']})")
        print(f"  Entry Ts: {t['entry_timestamp']} @ {t['entry_price']}")
        print(f"  MFE: {t['mfe_r']}R (Price: {t.get('metadata',{}).get('mfe_price')})")
        print(f"  D-03 Exit: {t['exit_reason']} @ {t['exit_price']} -> {t['net_r_fixed']:.2f}R")
        print(f"  H0 Exit: {h0_t['exit_reason']} @ {h0_t['exit_price']} -> {h0_t['net_r_fixed']:.2f}R")
        print(f"  Delta: {delta:+.2f}R => {classif}\n")

if __name__ == "__main__":
    main()
