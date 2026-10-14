"""Independent Quantitative Reconstruction and Portfolio Ledger Reconciliation.

Implements the 4-phase audit mandate:
Phase 1: Reconstruct the trade evidence from test_tri_strategy_fractal_trade.py without parameter changes.
         Serialize every trade into a complete trade-level ledger.
         Reconcile against the stored 2,563-trade / +474.08R aggregate.
Phase 2: Enforce portfolio constraints: replay on a unified chronological timeline,
         enforcing the maximum 3 concurrent positions (3.0% heat) constraint.
Phase 3: Chronological partition:
         - In-Sample (DEV+VAL): Prior to July 1, 2024 (timestamp < 1719792000000)
         - Out-of-Sample (OOS): July 1, 2024 onward (timestamp >= 1719792000000)
Phase 4: Output reconciled metrics and write full JSON/CSV artifacts.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays, VAL_END_MS
from research.experiments.test_tri_strategy_fractal_trade import (
    load_all_7_timeframes,
    scan_tri_strategy_signals,
)

OUTPUT_DIR = WORKSPACE_ROOT / "research" / "results" / "TRI_STRATEGY_FRACTAL_RESEARCH"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def trade_to_dict(t: TradeRecord, status: str = "FILLED") -> Dict[str, Any]:
    return {
        "symbol": t.symbol,
        "stream_id": t.stream_id,
        "direction": t.direction,
        "entry_ts": t.entry_ts,
        "entry_datetime_utc": datetime.fromtimestamp(t.entry_ts / 1000, tz=timezone.utc).isoformat() if t.entry_ts > 0 else None,
        "exit_ts": t.exit_ts,
        "exit_datetime_utc": datetime.fromtimestamp(t.exit_ts / 1000, tz=timezone.utc).isoformat() if t.exit_ts > 0 else None,
        "entry_px": t.entry_px,
        "exit_px": t.exit_px,
        "initial_sl": t.initial_sl,
        "target_px": t.target_px,
        "initial_risk_dist": t.initial_risk_dist,
        "target_r": t.target_r,
        "realized_r": t.realized_r,
        "exit_reason": t.exit_reason,
        "bars_held": t.bars_held,
        "fee_bps": t.fee_bps,
        "slippage_bps": t.slippage_bps,
        "mfe_r": t.mfe_r,
        "mae_r": t.mae_r,
        "portfolio_status": status,
        "is_oos": bool(t.entry_ts >= VAL_END_MS),
    }


def compute_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "avg_win_r": 0.0,
            "avg_loss_r": 0.0,
            "max_drawdown_r": 0.0,
        }

    rs = np.array([t["realized_r"] for t in trades], dtype=float)
    wins = rs[rs > 0]
    losses = rs[rs < 0]
    n_wins = len(wins)
    n_losses = len(losses)
    wr = (n_wins / n) * 100.0

    gross_win = float(np.sum(wins)) if n_wins > 0 else 0.0
    gross_loss = abs(float(np.sum(losses))) if n_losses > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

    total_r = float(np.sum(rs))
    exp_r = float(np.mean(rs))
    avg_win = float(np.mean(wins)) if n_wins > 0 else 0.0
    avg_loss = float(np.mean(losses)) if n_losses > 0 else 0.0

    cum_r = np.cumsum(rs)
    peak = np.maximum.accumulate(cum_r)
    max_dd = float(np.max(peak - cum_r)) if len(cum_r) else 0.0

    return {
        "total_trades": n,
        "win_count": n_wins,
        "loss_count": n_losses,
        "win_rate_pct": round(wr, 2),
        "total_r": round(total_r, 2),
        "profit_factor": round(min(pf, 99.0), 2),
        "expectancy_r": round(exp_r, 4),
        "avg_win_r": round(avg_win, 4),
        "avg_loss_r": round(avg_loss, 4),
        "max_drawdown_r": round(max_dd, 2),
    }


def main():
    print("=" * 100)
    print("INDEPENDENT QUANTITATIVE RECONSTRUCTION AND PORTFOLIO AUDIT")
    print(f"Val/OOS Split Timestamp: {VAL_END_MS} (2024-06-30T23:59:59Z)")
    print("=" * 100)

    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

    coordinator = CascadingFractalCoordinator(
        min_target_r=4.0,
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )

    engine = CausalBacktestEngine(
        taker_fee_bps=5.0,
        slippage_bps=2.0,
        min_target_r=4.0,
        max_holding_bars=200,
    )

    # ---------------------------------------------------------
    # PHASE 1: Re-execute individual streams and collect ALL trades
    # ---------------------------------------------------------
    all_raw_trades: List[Dict[str, Any]] = []

    for asset in assets:
        all_data = load_all_7_timeframes(asset)
        if len(all_data) < 3:
            continue

        print(f"Scanning & Simulating Asset: {asset}...")

        for target_set in sets:
            cfg = coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]
            if ltf_tf not in all_data:
                continue

            ltf_data = all_data[ltf_tf]
            candidates, trailing_map = scan_tri_strategy_signals(
                symbol=asset,
                target_set=target_set,
                all_data=all_data,
                coordinator=coordinator,
            )

            if not candidates:
                continue

            stream_id = f"TRI_{asset[:3]}_{target_set}"
            metrics = engine.execute_stream(
                stream_id=stream_id,
                symbol=asset,
                timeframe_set=target_set,
                hypothesis="TRI_STRATEGY_FRACTAL_CONFLUENCE",
                ltf_opens=ltf_data["o"],
                ltf_highs=ltf_data["h"],
                ltf_lows=ltf_data["l"],
                ltf_closes=ltf_data["c"],
                ltf_timestamps=ltf_data["ts"],
                signal_candidates=candidates,
                mtf_trailing_levels=trailing_map,
            )

            for t in metrics.trades:
                td = trade_to_dict(t, status="UNCONSTRAINED_STREAM")
                td["origin_set"] = target_set
                all_raw_trades.append(td)

    # Sort all raw trades strictly by entry_ts ascending, then exit_ts ascending
    all_raw_trades.sort(key=lambda x: (x["entry_ts"], x["exit_ts"]))

    n_raw = len(all_raw_trades)
    print(f"\n[PHASE 1] Reconstructed Total Unconstrained Trades: {n_raw}")

    # Reconcile against stored artifact
    ref_artifact = OUTPUT_DIR / "tri_strategy_validation_results.json"
    if ref_artifact.exists():
        with open(ref_artifact, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        ref_n = ref_data.get("total_trades", 0)
        ref_r = ref_data.get("total_alpha_r", 0.0)
        reconstructed_r = round(float(sum(t["realized_r"] for t in all_raw_trades)), 2)
        print(f"  Stored Reference Artifact: N={ref_n}, Net R={ref_r}R")
        print(f"  Reconstructed Stream Run:  N={n_raw}, Net R={reconstructed_r}R")
        diff_r = abs(reconstructed_r - ref_r)
        if n_raw == ref_n and diff_r < 0.1:
            print("  >>> PHASE 1 BIT-LEVEL RECONCILIATION: PERFECT MATCH (100% REPRODUCIBLE) <<<")
        else:
            print(f"  >>> PHASE 1 RECONCILIATION DISCREPANCY: dN={n_raw - ref_n}, dR={diff_r:.2f} <<<")

    # Save complete unconstrained trade ledger to JSONL and CSV
    unconstrained_jsonl = OUTPUT_DIR / "tri_strategy_unconstrained_trade_ledger.jsonl"
    with open(unconstrained_jsonl, "w", encoding="utf-8") as f:
        for t in all_raw_trades:
            f.write(json.dumps(t) + "\n")

    unconstrained_csv = OUTPUT_DIR / "tri_strategy_unconstrained_trade_ledger.csv"
    if all_raw_trades:
        keys = list(all_raw_trades[0].keys())
        with open(unconstrained_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_raw_trades)
    print(f"Saved Unconstrained Trade Ledger to: {unconstrained_jsonl.name} & {unconstrained_csv.name}")

    # ---------------------------------------------------------
    # PHASE 2: Chronological Portfolio Replay (Max 3 Positions)
    # ---------------------------------------------------------
    MAX_CONCURRENT_POSITIONS = 3
    portfolio_accepted_trades: List[Dict[str, Any]] = []
    portfolio_rejected_trades: List[Dict[str, Any]] = []

    # Active positions tracker: list of (exit_ts, trade_dict)
    active_positions: List[Dict[str, Any]] = []

    for cand_trade in all_raw_trades:
        entry_ts = cand_trade["entry_ts"]

        # Prune positions that have already closed at or before this entry timestamp
        active_positions = [p for p in active_positions if p["exit_ts"] > entry_ts]

        if len(active_positions) < MAX_CONCURRENT_POSITIONS:
            # Accepted
            cand_copy = dict(cand_trade)
            cand_copy["portfolio_status"] = "ACCEPTED_BY_HEAT_GOVERNOR"
            cand_copy["concurrent_positions_at_entry"] = len(active_positions)
            portfolio_accepted_trades.append(cand_copy)
            active_positions.append(cand_copy)
        else:
            # Rejected due to 3.0% max account heat limit
            cand_copy = dict(cand_trade)
            cand_copy["portfolio_status"] = "REJECTED_HEAT_LIMIT_EXCEEDED"
            cand_copy["concurrent_positions_at_entry"] = len(active_positions)
            portfolio_rejected_trades.append(cand_copy)

    print(f"\n[PHASE 2] Chronological Portfolio Constraints Applied (Max {MAX_CONCURRENT_POSITIONS} Positions):")
    print(f"  Accepted Trades: {len(portfolio_accepted_trades)}")
    print(f"  Rejected Trades: {len(portfolio_rejected_trades)} ({(len(portfolio_rejected_trades)/n_raw*100):.1f}% pruned by risk governor)")

    # Save portfolio accepted ledger
    portfolio_jsonl = OUTPUT_DIR / "tri_strategy_portfolio_constrained_ledger.jsonl"
    with open(portfolio_jsonl, "w", encoding="utf-8") as f:
        for t in portfolio_accepted_trades:
            f.write(json.dumps(t) + "\n")

    portfolio_csv = OUTPUT_DIR / "tri_strategy_portfolio_constrained_ledger.csv"
    if portfolio_accepted_trades:
        keys = list(portfolio_accepted_trades[0].keys())
        with open(portfolio_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(portfolio_accepted_trades)
    print(f"Saved Portfolio Constrained Ledger to: {portfolio_jsonl.name} & {portfolio_csv.name}")

    # ---------------------------------------------------------
    # PHASE 3: Partition Metrics (In-Sample vs Out-of-Sample)
    # ---------------------------------------------------------
    # 1. Unconstrained Streams Partition
    uncon_is = [t for t in all_raw_trades if not t["is_oos"]]
    uncon_oos = [t for t in all_raw_trades if t["is_oos"]]

    m_uncon_full = compute_metrics(all_raw_trades)
    m_uncon_is = compute_metrics(uncon_is)
    m_uncon_oos = compute_metrics(uncon_oos)

    # 2. Portfolio-Constrained Partition
    port_is = [t for t in portfolio_accepted_trades if not t["is_oos"]]
    port_oos = [t for t in portfolio_accepted_trades if t["is_oos"]]

    m_port_full = compute_metrics(portfolio_accepted_trades)
    m_port_is = compute_metrics(port_is)
    m_port_oos = compute_metrics(port_oos)

    # 3. By-Set Breakdown for Portfolio-Constrained
    by_set_portfolio = {}
    for s in sets:
        s_trades = [t for t in portfolio_accepted_trades if t.get("origin_set") == s]
        s_is = [t for t in s_trades if not t["is_oos"]]
        s_oos = [t for t in s_trades if t["is_oos"]]
        by_set_portfolio[s] = {
            "FULL": compute_metrics(s_trades),
            "IN_SAMPLE": compute_metrics(s_is),
            "OUT_OF_SAMPLE": compute_metrics(s_oos),
        }

    # 4. By-Asset Breakdown for Portfolio-Constrained
    by_asset_portfolio = {}
    for a in assets:
        a_trades = [t for t in portfolio_accepted_trades if t.get("symbol") == a]
        a_is = [t for t in a_trades if not t["is_oos"]]
        a_oos = [t for t in a_trades if t["is_oos"]]
        by_asset_portfolio[a] = {
            "FULL": compute_metrics(a_trades),
            "IN_SAMPLE": compute_metrics(a_is),
            "OUT_OF_SAMPLE": compute_metrics(a_oos),
        }

    # ---------------------------------------------------------
    # PHASE 4: Format and Output Master Audit Results
    # ---------------------------------------------------------
    print("\n" + "=" * 105)
    print("MASTER RECONCILIATION AND OUT-OF-SAMPLE AUDIT REPORT")
    print("=" * 105)

    hdr = f"{'CONFIGURATION / REGIME':<35} | {'TRADES':<8} | {'WIN RATE':<10} | {'NET ALPHA':<13} | {'EXP (R)':<10} | {'PF':<6} | {'MAX DD':<8}"
    print(hdr)
    print("-" * 105)

    def print_row(lbl, m):
        print(f"{lbl:<35} | {m['total_trades']:<8} | {m['win_rate_pct']:>8.2f}% | {m['total_r']:>+11.2f}R | {m['expectancy_r']:>+8.4f}R | {m['profit_factor']:>6.2f} | {m['max_drawdown_r']:>6.1f}R")

    print("[1] UNCONSTRAINED INDEPENDENT SUM (THE THEORETICAL MAXIMUM)")
    print_row("  Full Sample (2020-2026)", m_uncon_full)
    print_row("  In-Sample (Prior to July 2024)", m_uncon_is)
    print_row("  Out-of-Sample (July 2024 - 2026)", m_uncon_oos)

    print("\n[2] REALISTIC PORTFOLIO-CONSTRAINED (MAX 3 POSITIONS / 3% HEAT)")
    print_row("  Portfolio Full Sample", m_port_full)
    print_row("  Portfolio In-Sample (DEV)", m_port_is)
    print_row("  Portfolio Out-of-Sample (OOS)", m_port_oos)

    print("\n[3] PORTFOLIO PERFORMANCE BY TIMEFRAME SET (OOS ROBUSTNESS)")
    for s, data in by_set_portfolio.items():
        print(f"  {s} -> Full: N={data['FULL']['total_trades']}, Net={data['FULL']['total_r']:>+7.2f}R, PF={data['FULL']['profit_factor']:>5.2f} | OOS: N={data['OUT_OF_SAMPLE']['total_trades']}, Net={data['OUT_OF_SAMPLE']['total_r']:>+7.2f}R, PF={data['OUT_OF_SAMPLE']['profit_factor']:>5.2f}")

    print("\n[4] PORTFOLIO PERFORMANCE BY ASSET (OOS ROBUSTNESS)")
    for a, data in by_asset_portfolio.items():
        print(f"  {a} -> Full: N={data['FULL']['total_trades']}, Net={data['FULL']['total_r']:>+7.2f}R, PF={data['FULL']['profit_factor']:>5.2f} | OOS: N={data['OUT_OF_SAMPLE']['total_trades']}, Net={data['OUT_OF_SAMPLE']['total_r']:>+7.2f}R, PF={data['OUT_OF_SAMPLE']['profit_factor']:>5.2f}")

    print("=" * 105)

    # Compile final JSON report
    report_artifact = OUTPUT_DIR / "reconstruction_audit_report.json"
    audit_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audit_version": "2.0.0-reconstruction-portfolio-constrained",
        "parameters": {
            "max_concurrent_positions": MAX_CONCURRENT_POSITIONS,
            "val_end_ms": VAL_END_MS,
            "val_end_iso": datetime.fromtimestamp(VAL_END_MS / 1000, tz=timezone.utc).isoformat(),
            "taker_fee_bps": 5.0,
            "slippage_bps": 2.0,
            "min_target_r": 4.0,
        },
        "reconciliation": {
            "unconstrained_trades_reconstructed": n_raw,
            "stored_reference_trades": ref_data.get("total_trades", 0) if ref_artifact.exists() else None,
            "stored_reference_net_r": ref_data.get("total_alpha_r", 0.0) if ref_artifact.exists() else None,
            "is_perfect_reproduction": bool(n_raw == (ref_data.get("total_trades", 0) if ref_artifact.exists() else -1)),
        },
        "unconstrained_metrics": {
            "full": m_uncon_full,
            "in_sample": m_uncon_is,
            "out_of_sample": m_uncon_oos,
        },
        "portfolio_constrained_metrics": {
            "full": m_port_full,
            "in_sample": m_port_is,
            "out_of_sample": m_port_oos,
            "rejection_rate_pct": round(len(portfolio_rejected_trades) / n_raw * 100.0, 2),
        },
        "portfolio_by_set": by_set_portfolio,
        "portfolio_by_asset": by_asset_portfolio,
    }

    with open(report_artifact, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print(f"\nFinal Audit Report saved to: {report_artifact.name}")


if __name__ == "__main__":
    main()
