"""Evaluates top candidates through EdgeDiscoveryEngine, Benchmarks, and Null Hypothesis Lab.

Promotes qualified candidates to CHAMPION under the strict No-Degradation Promotion Law.
Outputs:
- research/results/discovery_engine/CHAMPION_CHALLENGER_REGISTRY.json
- research/results/discovery_engine/GOVERNANCE_AUDIT_SUMMARY.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from research.discovery.edge_discovery_engine import EdgeDiscoveryEngine
from research.experiments.run_phase_p_fractal_discovery import TIMEFRAME_SETS, load_series_arrays

DISCOVERY_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY"
GOVERNANCE_DIR = WORKSPACE_ROOT / "research" / "results" / "discovery_engine"
GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)


def run_governance():
    engine = EdgeDiscoveryEngine()

    # Select representative key candidates across assets, sets, and phases
    target_stream_ids = [
        "ETH_SET_2_HYP_A_PULLBACK",
        "BTC_SET_2_HYP_B_CONTINUATION",
        "BTC_SET_3_HYP_A_PULLBACK",
        "ETH_SET_3_HYP_A_PULLBACK",
        "SOL_SET_3_HYP_A_PULLBACK",
        "SOL_SET_4_HYP_B_CONTINUATION",
        "BNB_SET_2_HYP_B_CONTINUATION",
        "BTC_SET_5_HYP_B_CONTINUATION",  # Falsification candidate to prove rejection logic
    ]

    governance_audit = {}

    for sid in target_stream_ids:
        fpath = DISCOVERY_DIR / f"{sid}.json"
        if not fpath.exists():
            print(f"[Governance] Warning: {sid} not found in discovery results.")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        symbol = data["symbol"]
        tf_set = data["timeframe_set"]
        hyp = data["hypothesis"]
        phase_mode = "PULLBACK" if "PULLBACK" in hyp else "CONTINUATION"

        ltf_tf = TIMEFRAME_SETS[tf_set]["ltf"]
        ltf_data = load_series_arrays(symbol, ltf_tf)
        if not ltf_data:
            print(f"[Governance] Skipping {sid}: LTF data missing.")
            continue

        trades_raw = data.get("trades", [])
        real_trades = [
            TradeRecord(
                symbol=symbol,
                stream_id=sid,
                direction=t["direction"],
                entry_ts=t["entry_ts"],
                exit_ts=t["exit_ts"],
                entry_px=t["entry_px"],
                exit_px=t["exit_px"],
                initial_sl=t["initial_sl"],
                target_px=t["target_px"],
                initial_risk_dist=1.0,
                target_r=t["target_r"],
                realized_r=t["realized_r"],
                exit_reason=t["exit_reason"],
                bars_held=t["bars_held"],
                fee_bps=10.0,
                slippage_bps=4.0,
            )
            for t in trades_raw
        ]

        ts_to_idx = {ts: idx for idx, ts in enumerate(ltf_data["ts"])}
        real_cands = []
        for t in real_trades:
            entry_bar = ts_to_idx.get(t.entry_ts)
            sig_bar = max(0, entry_bar - 1) if entry_bar is not None else 0
            real_cands.append({
                "bar_index": sig_bar,
                "direction": t.direction,
                "entry_price": t.entry_px,
                "entry_px": t.entry_px,
                "stop_price": t.initial_sl,
                "stop_px": t.initial_sl,
                "target_price": t.target_px,
                "target_px": t.target_px,
                "target_r": t.target_r,
            })

        print(f"\n[Governance] Evaluating candidate {sid} (Trades: {len(real_trades)})...", flush=True)

        res = engine.evaluate_and_govern_challenger(
            challenger_id=sid,
            symbol=symbol,
            timeframe_set=tf_set,
            phase_mode=phase_mode,
            metrics_full=data["full_metrics"],
            metrics_dev=data["splits"]["DEV"],
            metrics_val=data["splits"]["VAL"],
            metrics_oos=data["splits"]["OOS"],
            ltf_data=ltf_data,
            real_candidates=real_cands,
            real_trades=real_trades,
        )

        governance_audit[sid] = res
        print(f"  -> Verdict: {res['promotion_verdict']} | Reason: {res['promotion_reason']}")
        print(f"  -> Null Test p-value: {res['null_test']['empirical_p_value']:.4f} (Falsified: {res['null_test']['is_falsified']})")
        print(f"  -> BM4 Trend Following Total R: {res['benchmarks']['BM_4_trend_following']['total_r']:+.2f}R")
        print(f"  -> BM6 Mean Reversion Total R:  {res['benchmarks']['BM_6_mean_reversion']['total_r']:+.2f}R")

    audit_file = GOVERNANCE_DIR / "GOVERNANCE_AUDIT_SUMMARY.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(governance_audit, f, indent=2)

    print(f"\n[Governance] Governance audit complete. Summary saved to {audit_file}")


if __name__ == "__main__":
    run_governance()
