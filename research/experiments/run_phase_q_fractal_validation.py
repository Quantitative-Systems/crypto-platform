"""Phase Q — Fractal State Engine vs. Baseline Comparative Validation.

Compares the new FractalStateEngine architecture (cross-timeframe coherence + 
confidence scoring + cross-set support) against the existing per-set baseline
from Phase P.

The experiment answers the 13 research questions defined in the mission:
1. Does the fractal relationship contain additional statistically valid edge?
2. Is cross-set coherence non-zero incremental value over independent sets?
3. Which sets are tradeable? Which are marginal?
4. Does alignment improve expectancy? By how much?
5. Is the edge robust under cost stress?
6. Does it transfer to out-of-universe assets?
7. What is the optimal confidence threshold?
8. Does CHOCH vs BOS conditioning survive fractal integration?
9. Is the fractal engine superior or is the per-set baseline sufficient?
10. What is the information value of each additional layer?
11. Walk-forward: Does it survive OOS?
12. Does double-counting inflate apparent edge?
13. Final verdict: strongest validated architecture.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from market_model.contracts import MarketPhaseType, MarketState, StructuralBreakType, TrendDirection
from market_model.fractal_state_engine import (
    CrossSetCoherenceTracker,
    FractalAlignment,
    FractalBias,
    FractalHypothesis,
    FractalStateEngine,
    TIMEFRAME_SETS,
)
from market_model.state_generator import MarketStateGenerator
from research.experiments.mtf_strategy_coordinator import MTFStrategyCoordinator
from research.experiments.run_phase_p_fractal_discovery import (
    compute_extended_metrics,
    load_series_arrays,
    split_trades,
    DEV_END_MS,
    VAL_END_MS,
)

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_Q_FRACTAL_VALIDATION"


def load_all_timeframe_data(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    """Load all 7 timeframes for a given symbol."""
    all_data = {}
    for tf_label in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
        data = load_series_arrays(symbol, tf_label)
        if data is not None:
            all_data[tf_label] = data
    return all_data


def run_fractal_enhanced_stream(
    symbol: str,
    set_name: str,
    hypothesis_type: str,  # "PULLBACK" or "CONTINUATION"
    all_data: Dict[str, Dict[str, np.ndarray]],
    fractal_engine: Optional[FractalStateEngine] = None,
    min_confidence: float = 0.0,
    min_target_r: float = 4.0,
    taker_fee_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """Run a fractal-enhanced backtest for a single set/hypothesis combo.
    
    Key difference from baseline: uses cross-set alignment and confidence scoring
    to filter/rank trade candidates.
    """
    cfg = TIMEFRAME_SETS[set_name]
    htf_tf = cfg["htf"]
    mtf_tf = cfg["mtf"]
    ltf_tf = cfg["ltf"]

    htf_data = all_data.get(htf_tf)
    mtf_data = all_data.get(mtf_tf)
    ltf_data = all_data.get(ltf_tf)

    if htf_data is None or mtf_data is None or ltf_data is None:
        return None

    # Initialize the fractal engine with ALL timeframe data if not provided
    if fractal_engine is None:
        fractal_engine = FractalStateEngine(symbol=symbol)
        fractal_engine.load_data(all_data)

    # Initialize the per-set coordinator (same as baseline)
    hyp_str = "PULLBACK" if hypothesis_type == "PULLBACK" else "CONTINUATION"
    coordinator = MTFStrategyCoordinator(
        timeframe_set_id=set_name,
        htf_label=htf_tf,
        mtf_label=mtf_tf,
        ltf_label=ltf_tf,
        hypothesis_type=hyp_str,
        min_target_r=min_target_r,
    )

    # First: get baseline candidates (same as Phase P)
    candidates, mtf_trailing_map = coordinator.scan_signals(
        symbol=symbol,
        htf_data=htf_data,
        mtf_data=mtf_data,
        ltf_data=ltf_data,
    )

    # Now: apply fractal enrichment to each candidate
    enriched_candidates = []
    fractal_metadata = []
    coherence = CrossSetCoherenceTracker()
    target_tfs = {"1M", "1w", "1d", "4h", "1h", mtf_tf, ltf_tf}

    for cand in candidates:
        bar_idx = cand["bar_index"]
        eval_ts = int(ltf_data["ts"][bar_idx])

        # Compute full fractal state at this point
        node = fractal_engine.evaluate_at(eval_ts, target_tfs=target_tfs)

        # Get fractal hypothesis
        hyp = fractal_engine.hypothesis_engine.evaluate_hypothesis(node, set_name, hypothesis_type)

        # Deduplication: check coherence
        break_type = cand.get("meta", {}).get("break_type", "UNKNOWN")
        is_new = coherence.register_event(ltf_tf, eval_ts, break_type, set_name)

        # Compute fractal enrichment
        alignment = node.get_alignment_for_set(set_name)
        cross_support = fractal_engine.hypothesis_engine._count_cross_set_support(
            node, set_name, cand["direction"]
        )
        confidence = hyp.confidence_score if hyp else 0.3

        # Apply confidence filter
        if confidence < min_confidence:
            continue

        # Enrich candidate metadata
        enriched = dict(cand)
        enriched["meta"] = dict(cand.get("meta", {}))
        enriched["meta"]["fractal_alignment"] = alignment.value
        enriched["meta"]["fractal_bias"] = node.fractal_bias.value
        enriched["meta"]["cross_set_support"] = cross_support
        enriched["meta"]["confidence_score"] = confidence
        enriched["meta"]["is_unique_event"] = is_new

        enriched_candidates.append(enriched)
        fractal_metadata.append({
            "bar_index": bar_idx,
            "alignment": alignment.value,
            "bias": node.fractal_bias.value,
            "cross_support": cross_support,
            "confidence": confidence,
            "active_sets": node.active_sets,
        })

    # Execute backtest on enriched candidates
    stream_id = f"FRAC_{symbol[:3]}_{set_name}_{hypothesis_type}"
    engine = CausalBacktestEngine(
        taker_fee_bps=taker_fee_bps,
        slippage_bps=slippage_bps,
        min_target_r=min_target_r,
    )

    metrics = engine.execute_stream(
        stream_id=stream_id,
        symbol=symbol,
        timeframe_set=set_name,
        hypothesis=f"HYP_{'A' if hypothesis_type == 'PULLBACK' else 'B'}_{hypothesis_type}",
        ltf_opens=ltf_data["o"],
        ltf_highs=ltf_data["h"],
        ltf_lows=ltf_data["l"],
        ltf_closes=ltf_data["c"],
        ltf_timestamps=ltf_data["ts"],
        signal_candidates=enriched_candidates,
        mtf_trailing_levels=mtf_trailing_map,
    )

    splits = split_trades(metrics.trades)
    split_metrics = {name: compute_extended_metrics(t_list) for name, t_list in splits.items()}

    # Analyze alignment-conditioned performance
    alignment_groups = {}
    for trade in metrics.trades:
        align = trade.meta.get("fractal_alignment", "UNKNOWN")
        if align not in alignment_groups:
            alignment_groups[align] = []
        alignment_groups[align].append(trade)

    alignment_metrics = {}
    for align_name, trades in alignment_groups.items():
        alignment_metrics[align_name] = compute_extended_metrics(trades)

    # Analyze confidence-conditioned performance
    conf_high = [t for t in metrics.trades if t.meta.get("confidence_score", 0) >= 0.6]
    conf_low = [t for t in metrics.trades if t.meta.get("confidence_score", 0) < 0.6]

    confidence_metrics = {
        "high_confidence_gte_0.6": compute_extended_metrics(conf_high),
        "low_confidence_lt_0.6": compute_extended_metrics(conf_low),
    }

    # Analyze cross-set support conditioning
    support_groups = {}
    for trade in metrics.trades:
        sup = trade.meta.get("cross_set_support", 0)
        key = f"support_{sup}"
        if key not in support_groups:
            support_groups[key] = []
        support_groups[key].append(trade)

    support_metrics = {k: compute_extended_metrics(v) for k, v in support_groups.items()}

    return {
        "stream_id": stream_id,
        "symbol": symbol,
        "set_name": set_name,
        "hypothesis_type": hypothesis_type,
        "min_confidence": min_confidence,
        "baseline_candidate_count": len(candidates),
        "fractal_enriched_count": len(enriched_candidates),
        "filter_rate": round(1.0 - len(enriched_candidates) / max(len(candidates), 1), 4),
        "full_metrics": split_metrics["FULL"],
        "splits": split_metrics,
        "alignment_conditioned": alignment_metrics,
        "confidence_conditioned": confidence_metrics,
        "cross_set_support_conditioned": support_metrics,
        "trades": [
            {
                "entry_ts": t.entry_ts,
                "exit_ts": t.exit_ts,
                "direction": t.direction,
                "entry_px": t.entry_px,
                "exit_px": t.exit_px,
                "realized_r": t.realized_r,
                "exit_reason": t.exit_reason,
                "bars_held": t.bars_held,
                "meta": t.meta,
            }
            for t in metrics.trades
        ],
    }


def run_confidence_threshold_sweep(
    symbol: str,
    set_name: str,
    hypothesis_type: str,
    all_data: Dict[str, Dict[str, np.ndarray]],
    fractal_engine: Optional[FractalStateEngine] = None,
) -> Dict[str, Any]:
    """Sweep confidence thresholds to find optimal filtering level."""
    thresholds = [0.0, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    results = {}

    for thresh in thresholds:
        res = run_fractal_enhanced_stream(
            symbol=symbol,
            set_name=set_name,
            hypothesis_type=hypothesis_type,
            all_data=all_data,
            fractal_engine=fractal_engine,
            min_confidence=thresh,
        )
        if res:
            fm = res["full_metrics"]
            results[f"threshold_{thresh:.2f}"] = {
                "threshold": thresh,
                "total_trades": fm["total_trades"],
                "expectancy_r": fm["expectancy_r"],
                "total_r": fm["total_r"],
                "profit_factor": fm["profit_factor"],
                "win_rate": fm["win_rate"],
                "trimmed_expectancy_r": fm["trimmed_expectancy_r"],
            }

    return results


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]
    hypotheses = ["PULLBACK", "CONTINUATION"]

    print("=" * 100)
    print("PHASE Q — FRACTAL STATE ENGINE vs. BASELINE COMPARATIVE VALIDATION")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Assets: {assets}")
    print(f"Sets: {sets}")
    print(f"Hypotheses: {hypotheses}")
    print("=" * 100)

    # ============================================================
    # 1. FRACTAL-ENHANCED MATRIX (Asset x Set x Hypothesis)
    # ============================================================
    print("\n[1/5] Running Fractal-Enhanced Matrix...")
    fractal_results: Dict[str, Any] = {}
    all_fractal_trades: List[Dict[str, Any]] = []

    for asset in assets:
        print(f"\n  Loading all timeframe data for {asset}...")
        all_data = load_all_timeframe_data(asset)
        print(f"  Available timeframes: {list(all_data.keys())}")
        engine = FractalStateEngine(symbol=asset)
        engine.load_data(all_data)

        for tf_set in sets:
            for hyp in hypotheses:
                stream_file = RESULTS_DIR / f"FRAC_{asset[:3]}_{tf_set}_{hyp}.json"
                res = None
                if stream_file.exists():
                    try:
                        with open(stream_file, "r", encoding="utf-8") as f:
                            res = json.load(f)
                        elapsed = 0.0
                    except Exception:
                        res = None

                if res is None:
                    t0 = time.time()
                    res = run_fractal_enhanced_stream(asset, tf_set, hyp, all_data, fractal_engine=engine)
                    elapsed = round(time.time() - t0, 2)
                    if res:
                        with open(stream_file, "w", encoding="utf-8") as f:
                            json.dump(res, f, indent=2)

                if res:
                    stream_id = res["stream_id"]
                    fractal_results[stream_id] = res
                    all_fractal_trades.extend(res["trades"])
                    fm = res["full_metrics"]
                    sm = res["splits"]
                    print(
                        f"  [{stream_id:40s}] N={fm['total_trades']:>4} | WR={fm['win_rate']*100:>5.1f}% | "
                        f"ExpR={fm['expectancy_r']:>7.4f} | TotR={fm['total_r']:>8.2f} | PF={fm['profit_factor']:>6.3f} | "
                        f"DEV={sm['DEV']['total_r']:>7.2f} | OOS={sm['OOS']['total_r']:>7.2f} | "
                        f"Filter={res['filter_rate']*100:>4.1f}% | {elapsed:.1f}s",
                        flush=True,
                    )

    # ============================================================
    # 2. LOAD BASELINE RESULTS FOR COMPARISON
    # ============================================================
    print("\n[2/5] Loading Phase P Baseline Results for Comparison...")
    baseline_path = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY" / "master_phase_p_discovery.json"
    baseline_data = {}
    if baseline_path.exists():
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
    else:
        print("  [WARN] Phase P baseline not found. Cannot compare.")

    # ============================================================
    # 3. COMPARATIVE ANALYSIS
    # ============================================================
    print("\n[3/5] Computing Comparative Analysis (Fractal vs. Baseline)...")
    comparative = {}

    baseline_streams = baseline_data.get("streams", {})
    for frac_id, frac_res in fractal_results.items():
        # Map fractal ID back to baseline ID
        parts = frac_id.replace("FRAC_", "").split("_")
        asset_key = parts[0]
        set_key = parts[1] + "_" + parts[2]
        hyp_key = "HYP_A_PULLBACK" if parts[3] == "PULLBACK" else "HYP_B_CONTINUATION"
        baseline_id = f"{asset_key}_{set_key}_{hyp_key}"

        baseline_fm = baseline_streams.get(baseline_id, {}).get("full", {})

        frac_fm = frac_res["full_metrics"]

        if baseline_fm and baseline_fm.get("total_trades", 0) > 0:
            delta_exp_r = frac_fm["expectancy_r"] - baseline_fm["expectancy_r"]
            delta_total_r = frac_fm["total_r"] - baseline_fm["total_r"]
            delta_wr = frac_fm["win_rate"] - baseline_fm["win_rate"]
            delta_pf = frac_fm["profit_factor"] - baseline_fm["profit_factor"]
            trade_count_diff = frac_fm["total_trades"] - baseline_fm["total_trades"]

            comparative[frac_id] = {
                "baseline_id": baseline_id,
                "baseline_n": baseline_fm["total_trades"],
                "fractal_n": frac_fm["total_trades"],
                "trade_count_delta": trade_count_diff,
                "baseline_exp_r": baseline_fm["expectancy_r"],
                "fractal_exp_r": frac_fm["expectancy_r"],
                "delta_exp_r": round(delta_exp_r, 4),
                "baseline_total_r": baseline_fm["total_r"],
                "fractal_total_r": frac_fm["total_r"],
                "delta_total_r": round(delta_total_r, 2),
                "baseline_pf": baseline_fm["profit_factor"],
                "fractal_pf": frac_fm["profit_factor"],
                "delta_pf": round(delta_pf, 3),
                "baseline_wr": baseline_fm["win_rate"],
                "fractal_wr": frac_fm["win_rate"],
                "delta_wr": round(delta_wr, 4),
            }

    # Print comparison table
    print("\n" + "=" * 120)
    print("COMPARATIVE TABLE: FRACTAL vs. BASELINE")
    print("=" * 120)
    header = f"{'Stream':<40} {'B_N':>4} {'F_N':>4} {'B_ExpR':>7} {'F_ExpR':>7} {'dExpR':>7} {'B_TotR':>8} {'F_TotR':>8} {'dTotR':>8} {'B_PF':>6} {'F_PF':>6}"
    print(header)
    print("-" * 120)

    total_delta_exp = 0
    total_delta_r = 0
    count = 0

    for frac_id, comp in sorted(comparative.items()):
        print(
            f"{frac_id:<40} "
            f"{comp['baseline_n']:>4} {comp['fractal_n']:>4} "
            f"{comp['baseline_exp_r']:>7.4f} {comp['fractal_exp_r']:>7.4f} {comp['delta_exp_r']:>+7.4f} "
            f"{comp['baseline_total_r']:>8.2f} {comp['fractal_total_r']:>8.2f} {comp['delta_total_r']:>+8.2f} "
            f"{comp['baseline_pf']:>6.3f} {comp['fractal_pf']:>6.3f}",
            flush=True,
        )
        total_delta_exp += comp["delta_exp_r"]
        total_delta_r += comp["delta_total_r"]
        count += 1

    if count > 0:
        print("-" * 120)
        print(f"{'AVERAGE DELTA':<40} {'':>4} {'':>4} {'':>7} {'':>7} {total_delta_exp/count:>+7.4f} {'':>8} {'':>8} {total_delta_r/count:>+8.2f}")

    # ============================================================
    # 4. ALIGNMENT-CONDITIONED EDGE ANALYSIS
    # ============================================================
    print("\n[4/5] Alignment-Conditioned Edge Analysis...")
    alignment_agg: Dict[str, List[Dict]] = {}
    for frac_id, frac_res in fractal_results.items():
        for align_name, align_metrics in frac_res.get("alignment_conditioned", {}).items():
            if align_name not in alignment_agg:
                alignment_agg[align_name] = []
            alignment_agg[align_name].append(align_metrics)

    print("\nAGGREGATE ALIGNMENT PERFORMANCE:")
    print(f"{'Alignment':<25} {'Total N':>8} {'Wtd ExpR':>9} {'Sum TotR':>10} {'Avg WR':>7}")
    print("-" * 65)
    for align_name in sorted(alignment_agg.keys()):
        metrics_list = alignment_agg[align_name]
        total_n = sum(m["total_trades"] for m in metrics_list)
        if total_n == 0:
            continue
        wtd_exp = sum(m["expectancy_r"] * m["total_trades"] for m in metrics_list) / total_n
        sum_r = sum(m["total_r"] for m in metrics_list)
        avg_wr = sum(m["win_rate"] * m["total_trades"] for m in metrics_list) / total_n
        print(f"{align_name:<25} {total_n:>8} {wtd_exp:>9.4f} {sum_r:>10.2f} {avg_wr*100:>6.1f}%")

    # ============================================================
    # 5. CONFIDENCE THRESHOLD SWEEP
    # ============================================================
    print("\n[5/5] Confidence Threshold Sweep (BTC SET_2, ETH SET_3)...")
    btc_data = load_all_timeframe_data("BTCUSDT")
    eth_data = load_all_timeframe_data("ETHUSDT")

    btc_engine = FractalStateEngine(symbol="BTCUSDT")
    btc_engine.load_data(btc_data)
    sweep_btc = run_confidence_threshold_sweep("BTCUSDT", "SET_2", "CONTINUATION", btc_data, fractal_engine=btc_engine)

    eth_engine = FractalStateEngine(symbol="ETHUSDT")
    eth_engine.load_data(eth_data)
    sweep_eth = run_confidence_threshold_sweep("ETHUSDT", "SET_3", "CONTINUATION", eth_data, fractal_engine=eth_engine)

    print("\nBTC SET_2 CONTINUATION — Confidence Threshold Sweep:")
    print(f"{'Threshold':<12} {'N':>5} {'ExpR':>8} {'TotR':>9} {'PF':>7} {'WR':>6} {'TrimR':>8}")
    for k, v in sorted(sweep_btc.items()):
        print(f"{v['threshold']:>10.2f}   {v['total_trades']:>5} {v['expectancy_r']:>8.4f} {v['total_r']:>9.2f} {v['profit_factor']:>7.3f} {v['win_rate']*100:>5.1f}% {v['trimmed_expectancy_r']:>8.4f}")

    print("\nETH SET_3 CONTINUATION — Confidence Threshold Sweep:")
    print(f"{'Threshold':<12} {'N':>5} {'ExpR':>8} {'TotR':>9} {'PF':>7} {'WR':>6} {'TrimR':>8}")
    for k, v in sorted(sweep_eth.items()):
        print(f"{v['threshold']:>10.2f}   {v['total_trades']:>5} {v['expectancy_r']:>8.4f} {v['total_r']:>9.2f} {v['profit_factor']:>7.3f} {v['win_rate']*100:>5.1f}% {v['trimmed_expectancy_r']:>8.4f}")

    # ============================================================
    # COMPILE MASTER RESULTS
    # ============================================================
    master_artifact = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "PHASE_Q_FRACTAL_VS_BASELINE",
        "total_fractal_streams": len(fractal_results),
        "total_fractal_trades": len(all_fractal_trades),
        "fractal_streams": {
            k: {
                "full": v["full_metrics"],
                "splits": v["splits"],
                "alignment_conditioned": v.get("alignment_conditioned", {}),
                "confidence_conditioned": v.get("confidence_conditioned", {}),
                "cross_set_support_conditioned": v.get("cross_set_support_conditioned", {}),
                "filter_rate": v.get("filter_rate", 0.0),
            }
            for k, v in fractal_results.items()
        },
        "comparative_analysis": comparative,
        "alignment_aggregate": {
            k: {
                "total_n": sum(m["total_trades"] for m in v),
                "wtd_exp_r": round(sum(m["expectancy_r"] * m["total_trades"] for m in v) / max(sum(m["total_trades"] for m in v), 1), 4),
                "sum_total_r": round(sum(m["total_r"] for m in v), 2),
            }
            for k, v in alignment_agg.items()
        },
        "confidence_threshold_sweep": {
            "BTC_SET_2_CONTINUATION": sweep_btc,
            "ETH_SET_3_CONTINUATION": sweep_eth,
        },
    }

    out_file = RESULTS_DIR / "master_phase_q_fractal_validation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master_artifact, f, indent=2)

    print("\n" + "=" * 100)
    print(f"PHASE Q COMPLETE! Results: {out_file}")
    print("=" * 100)


if __name__ == "__main__":
    main()
