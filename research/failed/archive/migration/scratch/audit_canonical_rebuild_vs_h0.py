"""
Forensic Audit: Canonical Strategy Rebuild vs Frozen H0 Control (2021-2022 Development Partition)
Compares:
- scratch/canonical_rebuild_dev_results.json
- scratch/h0_dev_control_results.json
"""

import json
import sys
import numpy as np
import pandas as pd

def run_audit():
    h0_path = "/home/mrcn2/crypto-platform/scratch/h0_dev_control_results.json"
    rebuild_path = "/home/mrcn2/crypto-platform/scratch/canonical_rebuild_dev_results.json"

    with open(h0_path, "r") as f:
        h0 = json.load(f)
    with open(rebuild_path, "r") as f:
        reb = json.load(f)

    h0_agg = h0.get("aggregate_performance", {})
    reb_agg = reb.get("aggregate_performance", {})

    print("=" * 90)
    print("FORENSIC BENCHMARK AUDIT: CANONICAL REBUILD vs FROZEN H0 CONTROL")
    print("Temporal Partition: 2021-01-01 to 2022-12-31 (Strict Development Partition)")
    print("=" * 90)

    print(f"\n{'Metric':<35} | {'Frozen H0 Control':<20} | {'Canonical Rebuild':<20} | {'Delta':<15}")
    print("-" * 95)

    metrics = [
        ("Total Trades", h0_agg.get("total_trades", 0), reb_agg.get("total_trades", 0), "int"),
        ("Unique Economic Setups", h0_agg.get("unique_economic_setups", 0), reb_agg.get("unique_economic_setups", 0), "int"),
        ("Net Realized R", h0_agg.get("net_realized_r", 0.0), reb_agg.get("net_realized_r", 0.0), "r"),
        ("Gross Realized R", h0_agg.get("gross_realized_r", 0.0), reb_agg.get("gross_realized_r", 0.0), "r"),
        ("Win Rate (%)", h0_agg.get("win_rate_pct", 0.0), reb_agg.get("win_rate_pct", 0.0), "pct"),
        ("Expectancy (R/trade)", h0_agg.get("expectancy_r", 0.0), reb_agg.get("expectancy_r", 0.0), "r"),
        ("Profit Factor", h0_agg.get("profit_factor", 0.0), reb_agg.get("profit_factor", 0.0), "num"),
        ("Max Drawdown (R)", h0_agg.get("max_drawdown_r", 0.0), reb_agg.get("max_drawdown_r", 0.0), "r"),
        ("Wins / Losses / BE", 
         f"{h0_agg.get('wins', 0)}/{h0_agg.get('losses', 0)}/{h0_agg.get('breakevens', 0)}",
         f"{reb_agg.get('wins', 0)}/{reb_agg.get('losses', 0)}/{reb_agg.get('breakevens', 0)}",
         "str"),
        ("Avg Winner (R)", h0_agg.get("avg_winner_r", 0.0), reb_agg.get("avg_winner_r", 0.0), "r"),
        ("Avg Loser (R)", h0_agg.get("avg_loser_r", 0.0), reb_agg.get("avg_loser_r", 0.0), "r"),
    ]

    for label, v_h0, v_reb, mtype in metrics:
        if mtype == "int":
            delta = v_reb - v_h0
            d_str = f"{delta:+d}"
            print(f"{label:<35} | {v_h0:<20} | {v_reb:<20} | {d_str:<15}")
        elif mtype == "r":
            delta = float(v_reb) - float(v_h0)
            d_str = f"{delta:+.2f}R"
            print(f"{label:<35} | {float(v_h0):.2f}R{'':<14} | {float(v_reb):.2f}R{'':<14} | {d_str:<15}")
        elif mtype == "pct":
            delta = float(v_reb) - float(v_h0)
            d_str = f"{delta:+.1f}%"
            print(f"{label:<35} | {float(v_h0):.1f}%{'':<15} | {float(v_reb):.1f}%{'':<15} | {d_str:<15}")
        elif mtype == "num":
            delta = float(v_reb) - float(v_h0)
            d_str = f"{delta:+.2f}"
            print(f"{label:<35} | {float(v_h0):.2f}{'':<16} | {float(v_reb):.2f}{'':<16} | {d_str:<15}")
        else:
            print(f"{label:<35} | {str(v_h0):<20} | {str(v_reb):<20} | {'-':<15}")

    print("\n" + "=" * 90)
    print("EXIT ATTRIBUTION DISTRIBUTION")
    print("=" * 90)
    h0_exits = h0.get("exit_distribution", {})
    reb_exits = reb.get("exit_distribution", {})
    all_exit_keys = sorted(set(list(h0_exits.keys()) + list(reb_exits.keys())))
    print(f"{'Exit Type':<35} | {'H0 Count':<15} | {'Rebuild Count':<15} | {'Rebuild Share':<15}")
    print("-" * 85)
    total_reb = reb_agg.get("total_trades", 1) or 1
    for k in all_exit_keys:
        c_h0 = h0_exits.get(k, 0)
        c_reb = reb_exits.get(k, 0)
        sh = (c_reb / total_reb) * 100.0
        print(f"{k:<35} | {c_h0:<15} | {c_reb:<15} | {sh:.1f}%")

    print("\n" + "=" * 90)
    print("MFE / MAE FORENSICS")
    print("=" * 90)
    h0_exc = h0.get("excursion_forensics", {})
    reb_exc = reb.get("excursion_forensics", {})
    print(f"Mean MFE:   H0 = {h0_exc.get('mean_mfe_r', 0.0):.2f}R | Rebuild = {reb_exc.get('mean_mfe_r', 0.0):.2f}R")
    print(f"Median MFE: H0 = {h0_exc.get('median_mfe_r', 0.0):.2f}R | Rebuild = {reb_exc.get('median_mfe_r', 0.0):.2f}R")
    print(f"Mean MAE:   H0 = {h0_exc.get('mean_mae_r', 0.0):.2f}R | Rebuild = {reb_exc.get('mean_mae_r', 0.0):.2f}R")

    print("\n" + "=" * 90)
    print("PER-STREAM PERFORMANCE MATRIX (15 STREAMS)")
    print("=" * 90)
    h0_streams = h0.get("per_stream_performance", {})
    reb_streams = reb.get("per_stream_performance", {})
    all_streams = sorted(set(list(h0_streams.keys()) + list(reb_streams.keys())))

    print(f"{'Stream ID':<15} | {'H0 Trades':<10} | {'H0 Net R':<10} | {'Reb Trades':<10} | {'Reb Net R':<10} | {'Reb WR%':<8} | {'Status':<12}")
    print("-" * 85)
    for sid in all_streams:
        s_h0 = h0_streams.get(sid, {})
        s_reb = reb_streams.get(sid, {})
        t_h0 = s_h0.get("trades", 0)
        r_h0 = s_h0.get("net_r", 0.0)
        t_reb = s_reb.get("trades", 0)
        r_reb = s_reb.get("net_r", 0.0)
        wr_reb = s_reb.get("win_rate", 0.0)
        stat_reb = s_reb.get("status", "ZERO_TRADES" if t_reb == 0 else "ACTIVE")
        print(f"{sid:<15} | {t_h0:<10} | {r_h0:<10.2f} | {t_reb:<10} | {r_reb:<10.2f} | {wr_reb:<8.1f} | {stat_reb:<12}")

if __name__ == "__main__":
    run_audit()
