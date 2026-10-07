"""
Product 04 — Research Laboratory: Child Experiment Runner H1.1 (Early MTF Alignment Entry)
Parent Hypothesis: HTF_TREND_CONTINUATION_V1 (Baseline Control H1)
Trial ID: Trial 2

Runs the isolated H1.1 state machine across all 24 canonical streams:
- Universe: BTCUSDT, ETHUSDT, SOLUSDT
- Timeframe Sets: SET 1, SET 2, SET 3, SET 4
- Data Window: Full certified historical cache (2017-08-17 to 2026-09-01)
- Identical Risk, Cost, Causality, and Execution Invariants
"""

import os
import sys
import json
import time
import subprocess
import datetime as _dt
from typing import Dict, List, Any, Optional

import numpy as np

from market_intelligence.primitives import Candle
from market_data.data_certifier import DataCertifier
from market_data.dataset_manifest import DatasetManifestManager
from research.replayer.causal_replayer import CausalReplayer
from research.metrics.metrics_engine import MetricsEngine
from research.analytics.statistical_validator import StatisticalValidator
from platform_core.capital_barrier import CapitalBarrier, CapitalBarrierTier
from strategy_engine.hypotheses.h1_1_early_mtf_entry import H1_1_EarlyMtfAlignmentEntry


CACHE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "market_data", "cache"))
RESULTS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "results"))

ASSETS = ["BTC", "ETH", "SOL"]
HYPOTHESES = {
    "HYP_A_PULLBACK_RIDING": "PULLBACK",
    "HYP_B_CONTINUATION_RIDING": "CONTINUATION",
}
TF_LABELS = {
    "SET_1": ("1M", "1w", "1d"),
    "SET_2": ("1w", "1d", "4h"),
    "SET_3": ("1d", "4h", "1h"),
    "SET_4": ("4h", "1h", "15m"),
}

STRATEGY_VERSION = "v2.0-H1.1-EARLY-ENTRY"
CONTROL_INVARIANTS = [
    "MAX_RISK_FRACTION_1_PCT",
    "MIN_RR_FLOOR_4_0R",
    "MONOTONIC_MTF_STRUCTURAL_TRAILING",
    "ZERO_LOOKAHEAD_CAUSALITY",
    "ADVERSE_FIRST_INTRABAR_COLLISION",
    "EARLY_MTF_ALIGNMENT_RETEST_TRIGGER",
    "MTF_REALIGNMENT_CANDIDATE_ONLY",
]


def load_cached_candles(symbol: str, timeframe: str) -> List[Candle]:
    base = "BTCUSDT" if symbol == "BTC" else f"{symbol}USDT"
    tf_tag = timeframe if timeframe == "1M" else timeframe.lower()
    path = os.path.join(CACHE_DIR, f"binance_{base}_{tf_tag}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"[DATA GATE] Missing required dataset: {path}")
    with open(path, "r") as f:
        raw = json.load(f)
    if not isinstance(raw, list) or len(raw) < (60 if tf_tag == "1M" else 200):
        raise ValueError(f"[DATA GATE] Dataset too small/truncated: {path} ({len(raw)} rows)")
    candles = [
        Candle(timestamp=int(b[0] // 1000), open=float(b[1]), high=float(b[2]),
               low=float(b[3]), close=float(b[4]), volume=float(b[5]))
        for b in raw
    ]
    candles.sort(key=lambda c: c.timestamp)
    return candles


def run_one_stream(
    symbol: str,
    set_id: str,
    hypothesis_id: str,
    htf: str,
    mtf: str,
    ltf: str,
    data: Dict[str, List[Candle]],
    manifests: Dict[str, str],
    output_dir: str,
    initial_balance: float = 10000.0,
    taker_fee_rate: float = 0.0005,
    slippage_bps: float = 5.0,
) -> Dict[str, Any]:
    stream_key = f"{symbol}_{set_id}_{hypothesis_id}"
    
    # Instantiate isolated H1.1 hypothesis
    h1_1_hyp = H1_1_EarlyMtfAlignmentEntry()
    
    replayer = CausalReplayer(
        timeframe_set_id=set_id,
        initial_balance=initial_balance,
        maker_fee_rate=0.0,
        taker_fee_rate=taker_fee_rate,
        slippage_bps=slippage_bps,
        enable_mtf_trailing=True,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75,
        enable_regime_filter=False,
        cache_htf_mtf=True,
        htf_context_filter=HYPOTHESES[hypothesis_id],
        hypothesis=h1_1_hyp
    )

    t0 = time.time()
    out = replayer.run(
        symbol=f"{symbol}USDT",
        htf_candles=data[htf],
        mtf_candles=data[mtf],
        ltf_candles=data[ltf],
    )
    elapsed = time.time() - t0

    trades = out["closed_trades"]
    metrics = out["metrics"]

    artifact = {
        "provenance": {
            "experiment": "EXP_H1_1_EARLY_MTF_ALIGNMENT_ENTRY",
            "parent_hypothesis": "HTF_TREND_CONTINUATION_V1",
            "trial_id": 2,
            "stream_key": stream_key,
            "asset": symbol,
            "timeframe_set": set_id,
            "htf": htf,
            "mtf": mtf,
            "ltf": ltf,
            "hypothesis_id": "H1.1_EARLY_MTF_ALIGNMENT_ENTRY",
            "strategy_version": STRATEGY_VERSION,
            "control_invariants": CONTROL_INVARIANTS,
            "created_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "execution_model": "1.0.0-causal-adverse-first",
            "config": {
                "initial_balance": initial_balance,
                "taker_fee_rate": taker_fee_rate,
                "slippage_bps": slippage_bps,
                "enable_mtf_trailing": True,
                "enable_profit_lock": True,
                "lockin_r": 1.0,
                "giveback_r": 0.75,
                "cache_htf_mtf": True,
            },
            "candle_counts": {
                "htf": len(data[htf]),
                "mtf": len(data[mtf]),
                "ltf": len(data[ltf]),
            },
            "elapsed_sec": round(elapsed, 2),
        },
        "metrics": metrics,
        "trades": trades,
        "rejected_candidates": out.get("rejected_candidates", []),
        "rejection_funnel": out.get("rejection_funnel", {}),
    }

    out_path = os.path.join(output_dir, f"{stream_key}.json")
    with open(out_path, "w") as f:
        json.dump(artifact, f, indent=2)

    return artifact


def run_full_h1_1_matrix():
    t_start = time.time()
    ts_str = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(RESULTS_DIR, f"EXP_H1_1_{ts_str}")
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 90)
    print(f"[EXP H1.1] Launching H1.1 Early MTF Alignment Entry Matrix -> {out_dir}")
    print("=" * 90)

    # 1. Load Data
    candle_store: Dict[str, Dict[str, List[Candle]]] = {}
    for sym in ASSETS:
        candle_store[sym] = {}
        for tf in ["1M", "1w", "1d", "4h", "1h", "15m"]:
            candle_store[sym][tf] = load_cached_candles(sym, tf)
            print(f"  Loaded {sym} {tf}: {len(candle_store[sym][tf])} bars")

    # 2. Run Streams
    stream_results: Dict[str, Dict[str, Any]] = {}
    stream_idx = 0
    total_streams = len(ASSETS) * len(TF_LABELS) * len(HYPOTHESES)

    for sym in ASSETS:
        for set_id, (htf, mtf, ltf) in TF_LABELS.items():
            for hyp_id in HYPOTHESES:
                stream_idx += 1
                stream_key = f"{sym}_{set_id}_{hyp_id}"
                print(f"[{stream_idx:02d}/{total_streams:02d}] Running {stream_key}...", flush=True)
                
                res = run_one_stream(
                    symbol=sym,
                    set_id=set_id,
                    hypothesis_id=hyp_id,
                    htf=htf,
                    mtf=mtf,
                    ltf=ltf,
                    data=candle_store[sym],
                    manifests={},
                    output_dir=out_dir
                )
                stream_results[stream_key] = res
                n_tr = len(res.get("trades", []))
                exp_r = res.get("metrics", {}).get("mean_expectancy_r")
                print(f"      -> Trades: {n_tr} | E[R]: {exp_r}", flush=True)

    # 3. Master Aggregation
    all_trades: List[Dict[str, Any]] = []
    all_rejected: List[Dict[str, Any]] = []
    funnel_totals: Counter = Counter()

    for res in stream_results.values():
        for t in res.get("trades", []):
            all_trades.append(t)
        for r in res.get("rejected_candidates", []):
            all_rejected.append(r)
        for r_code, count in res.get("rejection_funnel", {}).items():
            funnel_totals[r_code] += count

    # Metrics
    r_multiples = [t.get("realized_rr", t.get("net_r", 0.0)) for t in all_trades]
    mfe_values = [t.get("mfe_r", 0.0) or t.get("metadata", {}).get("mfe_r", 0.0) for t in all_trades]
    mae_values = [t.get("mae_r", 0.0) or t.get("metadata", {}).get("mae_r", 0.0) for t in all_trades]
    
    n_trades = len(all_trades)
    wins = sum(1 for r in r_multiples if r > 0)
    net_r = sum(r_multiples)
    mean_exp_r = net_r / n_trades if n_trades > 0 else 0.0
    win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0
    
    gross_wins = sum(x for x in r_multiples if x > 0)
    gross_losses = abs(sum(x for x in r_multiples if x < 0))
    pf = (gross_wins / gross_losses) if gross_losses > 0 else 0.0
    
    # Block Bootstrap
    boot = StatisticalValidator.block_bootstrap_resample(r_multiples, block_size=4, n_resamples=1000) if n_trades > 0 else {
        "pct_5th": 0.0, "pct_95th": 0.0, "prob_positive_edge_pct": 0.0
    }

    master_summary = {
        "experiment": "EXP_H1_1_EARLY_MTF_ALIGNMENT_ENTRY",
        "parent_hypothesis": "HTF_TREND_CONTINUATION_V1",
        "trial_id": 2,
        "created_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "total_streams": total_streams,
        "total_candidates_evaluated": len(all_rejected) + n_trades,
        "total_trades": n_trades,
        "wins": wins,
        "losses": n_trades - wins,
        "win_rate_pct": round(win_rate, 2),
        "gross_realized_r": round(sum(t.get("gross_r", r) for t, r in zip(all_trades, r_multiples)), 4),
        "net_realized_r": round(net_r, 4),
        "mean_expectancy_r": round(mean_exp_r, 4),
        "profit_factor": round(pf, 2),
        "mean_mfe_r": round(sum(mfe_values) / len(mfe_values), 4) if mfe_values else 0.0,
        "mean_mae_r": round(sum(mae_values) / len(mae_values), 4) if mae_values else 0.0,
        "bootstrap_95_ci": [boot["pct_5th"], boot["pct_95th"]],
        "prob_positive_edge_pct": boot["prob_positive_edge_pct"],
        "rejection_funnel": dict(funnel_totals),
        "capital_barrier_tier": "REJECTED_RESEARCH_ONLY" if mean_exp_r <= 0.0 else "RESEARCH_VALIDATED"
    }

    master_path = os.path.join(out_dir, "MASTER_SUMMARY.json")
    with open(master_path, "w") as f:
        json.dump(master_summary, f, indent=2)

    print("\n" + "=" * 90)
    print("H1.1 EXPERIMENT MASTER SUMMARY")
    print("=" * 90)
    print(json.dumps(master_summary, indent=2))
    print(f"\n[OK] Full H1.1 matrix completed in {round(time.time() - t_start, 2)}s. Results at: {out_dir}")


if __name__ == "__main__":
    from collections import Counter
    run_full_h1_1_matrix()
