import json
import numpy as np

def load_json(path):
    with open(path) as f:
        return json.load(f)

d_h0 = load_json("scratch/canonical_h0_backtest_dev.json") if "canonical_h0_backtest_dev.json" in open("scratch/check_trades.py", "w").name else None
# Let find which H0 file has 29 trades
h0_trades = None
for p in ["scratch/exp_c1_dev.json", "scratch/canonical_h0_backtest_dev.json", "scratch/canonical_h0_corrected_dev_results.json"]:
    try:
        t = load_json(p)["all_trades"]
        if len(t) == 29:
            # Note: in exp_c1_dev.json, it is C1 management. H0 has exact same 29 trades but with H0 exit management.
            pass
    except:
        pass

d_c1 = load_json("scratch/exp_c1_dev.json")
d_d1 = load_json("scratch/exp_d1_dev.json")
d_e1 = load_json("scratch/exp_e1_dev.json")

c1_trades = d_c1["all_trades"]
d1_trades = d_d1["all_trades"]
e1_trades = d_e1["all_trades"]

# Reconstruct H0 metrics from frozen record:
# H0: N=29, Wins=2, Losses=27, BE=0, WR=6.9%, Gross=-13.1360R, Friction=2.3825R, Net=-15.5185R, E=-0.5351R, PF=0.3871, MaxDD=17.8421R, MaxConsec=13
# MFE/MAE for H0: same trade entries as C1! So MFE and MAE are identical to C1.

def get_stats(trades, name):
    n = len(trades)
    wins = [t for t in trades if t["net_r"] > 0.05]
    losses = [t for t in trades if t["net_r"] < -0.05]
    bes = [t for t in trades if abs(t["net_r"]) <= 0.05]
    wr = len(wins) / n * 100 if n else 0
    gross = sum(t.get("gross_r", t["net_r"]) for t in trades)
    net = sum(t["net_r"] for t in trades)
    friction = sum(t.get("fees_r", 0) + t.get("slippage_r", 0) + t.get("funding_r", 0) for t in trades)
    e = net / n if n else 0
    tot_win = sum(t["net_r"] for t in wins)
    tot_loss = abs(sum(t["net_r"] for t in losses))
    pf = tot_win / tot_loss if tot_loss > 0 else (999.0 if tot_win > 0 else 0.0)
    
    # DD
    eq = 0
    peak = 0
    max_dd = 0
    consec = 0
    max_consec = 0
    sorted_t = sorted(trades, key=lambda x: x.get("entry_timestamp", 0))
    for t in sorted_t:
        eq += t["net_r"]
        if eq > peak: peak = eq
        dd = peak - eq
        if dd > max_dd: max_dd = dd
        if t["net_r"] < -0.05:
            consec += 1
            if consec > max_consec: max_consec = consec
        else:
            consec = 0
            
    mfes = [t.get("mfe_r", 0.0) for t in trades]
    maes = [t.get("mae_r", 0.0) for t in trades]
    
    mfe_05 = sum(1 for m in mfes if m < 0.5)
    mfe_10 = sum(1 for m in mfes if m < 1.0)
    mfe_15 = sum(1 for m in mfes if m >= 1.5)
    mfe_20 = sum(1 for m in mfes if m >= 2.0)
    
    return {
        "name": name, "n": n, "wins": len(wins), "losses": len(losses), "bes": len(bes),
        "wr": wr, "gross": gross, "friction": friction, "net": net, "e": e, "pf": pf,
        "max_dd": max_dd, "max_consec": max_consec,
        "avg_mfe": float(np.mean(mfes)), "med_mfe": float(np.median(mfes)),
        "avg_mae": float(np.mean(maes)), "med_mae": float(np.median(maes)),
        "mfe_05": mfe_05, "mfe_05_pct": mfe_05/n*100,
        "mfe_10": mfe_10, "mfe_10_pct": mfe_10/n*100,
        "mfe_15": mfe_15, "mfe_15_pct": mfe_15/n*100,
        "mfe_20": mfe_20, "mfe_20_pct": mfe_20/n*100,
        "mfes": mfes, "maes": maes
    }

s_c1 = get_stats(c1_trades, "C1")
s_d1 = get_stats(d1_trades, "D1")
s_e1 = get_stats(e1_trades, "E1")

print("=== OVERALL COMPARISON ===")
print(f"Metric                    | {'H0 (Frozen)':<12} | {'C1':<12} | {'D1':<12} | {'E1':<12}")
print("-" * 75)
print(f"Executed Trades           | 29           | {s_c1['n']:<12} | {s_d1['n']:<12} | {s_e1['n']:<12}")
print(f"Wins                      | 2            | {s_c1['wins']:<12} | {s_d1['wins']:<12} | {s_e1['wins']:<12}")
print(f"Losses                    | 27           | {s_c1['losses']:<12} | {s_d1['losses']:<12} | {s_e1['losses']:<12}")
print(f"Breakevens                | 0            | {s_c1['bes']:<12} | {s_d1['bes']:<12} | {s_e1['bes']:<12}")
print(f"Win Rate                  | 6.90%        | {s_c1['wr']:.2f}%       | {s_d1['wr']:.2f}%       | {s_e1['wr']:.2f}%")
print(f"Gross R                   | -13.1360R    | {s_c1['gross']:+.4f}R   | {s_d1['gross']:+.4f}R   | {s_e1['gross']:+.4f}R")
print(f"Friction R                | 2.3825R      | {s_c1['friction']:.4f}R     | {s_d1['friction']:.4f}R     | {s_e1['friction']:.4f}R")
print(f"Net R                     | -15.5185R    | {s_c1['net']:+.4f}R   | {s_d1['net']:+.4f}R   | {s_e1['net']:+.4f}R")
print(f"Expectancy                | -0.5351R     | {s_c1['e']:+.4f}R    | {s_d1['e']:+.4f}R    | {s_e1['e']:+.4f}R")
print(f"Profit Factor             | 0.3871       | {s_c1['pf']:.4f}       | {s_d1['pf']:.4f}       | {s_e1['pf']:.4f}")
print(f"Max Drawdown              | 17.8421R     | {s_c1['max_dd']:.4f}R    | {s_d1['max_dd']:.4f}R    | {s_e1['max_dd']:.4f}R")
print(f"Max Consec Losses         | 13           | {s_c1['max_consec']:<12} | {s_d1['max_consec']:<12} | {s_e1['max_consec']:<12}")
print(f"Average MFE               | {s_c1['avg_mfe']:.2f}R         | {s_c1['avg_mfe']:.2f}R        | {s_d1['avg_mfe']:.2f}R        | {s_e1['avg_mfe']:.2f}R")
print(f"Median MFE                | {s_c1['med_mfe']:.2f}R         | {s_c1['med_mfe']:.2f}R        | {s_d1['med_mfe']:.2f}R        | {s_e1['med_mfe']:.2f}R")
print(f"Average MAE               | {s_c1['avg_mae']:.2f}R         | {s_c1['avg_mae']:.2f}R        | {s_d1['avg_mae']:.2f}R        | {s_e1['avg_mae']:.2f}R")
print(f"Median MAE                | {s_c1['med_mae']:.2f}R         | {s_c1['med_mae']:.2f}R        | {s_d1['med_mae']:.2f}R        | {s_e1['med_mae']:.2f}R")
print(f"MFE < 0.5R                | 14 (48.3%)   | {s_c1['mfe_05']} ({s_c1['mfe_05_pct']:.1f}%)   | {s_d1['mfe_05']} ({s_d1['mfe_05_pct']:.1f}%)   | {s_e1['mfe_05']} ({s_e1['mfe_05_pct']:.1f}%)")
print(f"MFE < 1.0R                | 19 (65.5%)   | {s_c1['mfe_10']} ({s_c1['mfe_10_pct']:.1f}%)   | {s_d1['mfe_10']} ({s_d1['mfe_10_pct']:.1f}%)   | {s_e1['mfe_10']} ({s_e1['mfe_10_pct']:.1f}%)")
print(f"MFE >= 1.5R               | 10 (34.5%)   | {s_c1['mfe_15']} ({s_c1['mfe_15_pct']:.1f}%)   | {s_d1['mfe_15']} ({s_d1['mfe_15_pct']:.1f}%)   | {s_e1['mfe_15']} ({s_e1['mfe_15_pct']:.1f}%)")
print(f"MFE >= 2.0R               | 6 (20.7%)    | {s_c1['mfe_20']} ({s_c1['mfe_20_pct']:.1f}%)   | {s_d1['mfe_20']} ({s_d1['mfe_20_pct']:.1f}%)   | {s_e1['mfe_20']} ({s_e1['mfe_20_pct']:.1f}%)")
