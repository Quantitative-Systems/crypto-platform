import json
import os
import sys
import numpy as np

sys.path.insert(0, "/home/mrcn2/crypto-platform")

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def compute_metrics(trades):
    n = len(trades)
    if n == 0:
        return {
            "n": 0, "wins": 0, "losses": 0, "be": 0, "win_rate": 0.0,
            "gross_r": 0.0, "friction_r": 0.0, "net_r": 0.0, "expectancy": 0.0,
            "profit_factor": 0.0, "max_dd": 0.0, "max_consec_losses": 0,
            "avg_mfe": 0.0, "median_mfe": 0.0, "avg_mae": 0.0, "median_mae": 0.0,
            "mfe_under_0_5": 0, "mfe_under_1_0": 0, "mfe_ge_1_5": 0, "mfe_ge_2_0": 0
        }

    wins = [t for t in trades if t.get("net_r", 0) > 0.05]
    losses = [t for t in trades if t.get("net_r", 0) < -0.05]
    bes = [t for t in trades if abs(t.get("net_r", 0)) <= 0.05]

    win_rate = (len(wins) / n) * 100
    gross_r = sum(t.get("gross_r", t.get("net_r", 0)) for t in trades)
    net_r = sum(t.get("net_r", 0) for t in trades)
    friction_r = sum((t.get("fees_r", 0) + t.get("slippage_r", 0) + t.get("funding_r", 0)) for t in trades)
    expectancy = net_r / n

    total_win_r = sum(t.get("net_r", 0) for t in wins)
    total_loss_r = abs(sum(t.get("net_r", 0) for t in losses))
    pf = (total_win_r / total_loss_r) if total_loss_r > 0 else (999.0 if total_win_r > 0 else 0.0)

    # Max Drawdown
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    sorted_trades = sorted(trades, key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)
    consec_losses = 0
    max_consec_losses = 0
    for t in sorted_trades:
        nr = t.get("net_r", 0)
        equity += nr
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
        if nr < -0.05:
            consec_losses += 1
            if consec_losses > max_consec_losses:
                max_consec_losses = consec_losses
        else:
            consec_losses = 0

    mfes = [t.get("mfe_r", 0) for t in trades]
    maes = [t.get("mae_r", 0) for t in trades]

    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "be": len(bes),
        "win_rate": win_rate,
        "gross_r": gross_r,
        "friction_r": friction_r,
        "net_r": net_r,
        "expectancy": expectancy,
        "profit_factor": pf,
        "max_dd": max_dd,
        "max_consec_losses": max_consec_losses,
        "avg_mfe": float(np.mean(mfes)) if mfes else 0.0,
        "median_mfe": float(np.median(mfes)) if mfes else 0.0,
        "avg_mae": float(np.mean(maes)) if maes else 0.0,
        "median_mae": float(np.median(maes)) if maes else 0.0,
        "mfe_under_0_5": sum(1 for m in mfes if m < 0.5),
        "mfe_under_1_0": sum(1 for m in mfes if m < 1.0),
        "mfe_ge_1_5": sum(1 for m in mfes if m >= 1.5),
        "mfe_ge_2_0": sum(1 for m in mfes if m >= 2.0),
    }

def main():
    d_e1 = load_json("scratch/exp_e1_dev.json")
    d_d1 = load_json("scratch/exp_d1_dev.json")
    d_c1 = load_json("scratch/canonical_c1_dev_results.json")
    d_h0 = load_json("scratch/canonical_h0_dev_results.json")

    if not d_e1:
        print("E1 results not ready yet.")
        return

    e1_trades = d_e1.get("all_trades", [])
    d1_trades = d_d1.get("all_trades", []) if d_d1 else []
    c1_trades = d_c1.get("all_trades", []) if d_c1 else []
    h0_trades = d_h0.get("all_trades", []) if d_h0 else []

    m_h0 = compute_metrics(h0_trades)
    m_c1 = compute_metrics(c1_trades)
    m_d1 = compute_metrics(d1_trades)
    m_e1 = compute_metrics(e1_trades)

    print("=" * 90)
    print(f"{'Metric':<25} | {'H0':<12} | {'C1':<12} | {'D1':<12} | {'E1':<12}")
    print("-" * 90)
    keys = [
        ("Executed Trades", "n", "{:d}"),
        ("Wins", "wins", "{:d}"),
        ("Losses", "losses", "{:d}"),
        ("Breakevens", "be", "{:d}"),
        ("Win Rate (%)", "win_rate", "{:.1f}%"),
        ("Gross R", "gross_r", "{:+.4f}R"),
        ("Friction R", "friction_r", "{:.4f}R"),
        ("Net R", "net_r", "{:+.4f}R"),
        ("Expectancy", "expectancy", "{:+.4f}R"),
        ("Profit Factor", "profit_factor", "{:.4f}"),
        ("Max Drawdown", "max_dd", "{:.4f}R"),
        ("Max Consec Losses", "max_consec_losses", "{:d}"),
        ("Average MFE", "avg_mfe", "{:.2f}R"),
        ("Median MFE", "median_mfe", "{:.2f}R"),
        ("Average MAE", "avg_mae", "{:.2f}R"),
        ("Median MAE", "median_mae", "{:.2f}R"),
        ("MFE < 0.5R", "mfe_under_0_5", "{:d}"),
        ("MFE < 1.0R", "mfe_under_1_0", "{:d}"),
        ("MFE >= 1.5R", "mfe_ge_1_5", "{:d}"),
        ("MFE >= 2.0R", "mfe_ge_2_0", "{:d}"),
    ]
    for label, k, fmt in keys:
        v_h0 = fmt.format(m_h0[k])
        v_c1 = fmt.format(m_c1[k])
        v_d1 = fmt.format(m_d1[k])
        v_e1 = fmt.format(m_e1[k])
        print(f"{label:<25} | {v_h0:<12} | {v_c1:<12} | {v_d1:<12} | {v_e1:<12}")
    print("=" * 90)

    # Opportunity Attrition Analysis: compare D1 trades with E1 trades
    print("\n" + "=" * 90)
    print("OPPORTUNITY-ATTRITION ANALYSIS (D1 Trades vs E1 Trades)")
    print("=" * 90)
    e1_trade_ids = {t["trade_id"] for t in e1_trades}
    e1_candidate_ids = {t["trade_id"].replace("cand_", "").split("_")[0] for t in e1_trades}

    omitted_from_e1 = [t for t in d1_trades if t["trade_id"] not in e1_trade_ids]
    retained_in_e1 = [t for t in d1_trades if t["trade_id"] in e1_trade_ids]

    print(f"Total D1 Trades: {len(d1_trades)}")
    print(f"Retained in E1:  {len(retained_in_e1)}")
    print(f"Omitted from E1: {len(omitted_from_e1)}")
    print("-" * 90)

    for i, t in enumerate(omitted_from_e1):
        sym = t.get("symbol")
        st = t.get("timeframe_set")
        ts = t.get("entry_timestamp")
        dir_ = t.get("direction")
        cid = t.get("trade_id")
        entry_p = t.get("entry_price")
        stop_p = t.get("initial_stop_price")
        target_p = t.get("target_price")
        rr = t.get("raw_rr")
        mfe = t.get("mfe_r")
        mae = t.get("mae_r")
        nr = t.get("net_r")
        exit_r = t.get("exit_reason")
        prov = t.get("metadata", {}).get("structural_provenance", {})
        trig = prov.get("ltf_entry_reason")

        print(f"[{i+1:02d}] {sym} | {st} | {dir_} | ts={ts} | trig={trig}")
        print(f"     ID: {cid}")
        print(f"     Would-be: Entry={entry_p} | SL={stop_p} | TP={target_p} | Planned RR={rr:.2f}R")
        print(f"     D1 Outcome: Net R={nr:+.4f}R | MFE={mfe:.2f}R | MAE={mae:.2f}R | Exit={exit_r}")

    # Winner Preservation
    print("\n" + "=" * 90)
    print("WINNER PRESERVATION DIAGNOSTIC")
    print("=" * 90)
    for target_winner in ["+4.11R", "+5.70R"]:
        print(f"Target Winner: {target_winner}")
    btc_e1_winners = [t for t in e1_trades if "BTC" in t.get("symbol", "") and t.get("net_r", 0) > 1.0]
    print(f"Preserved BTC Winners in E1: {len(btc_e1_winners)}")
    for w in btc_e1_winners:
        print(f"  {w.get('symbol')} | {w.get('timeframe_set')} | Entry ts={w.get('entry_timestamp')} | Net R={w.get('net_r'):+.4f}R | Exit={w.get('exit_reason')}")

if __name__ == "__main__":
    main()
