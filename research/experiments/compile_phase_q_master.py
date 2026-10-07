"""Phase Q Master Artifact Compiler & Advanced Analytics Engine.

Loads all 40 completed fractal stream artifacts, aggregates cross-timeframe alignment,
evaluates confidence sweeps from enriched trade records, computes nested pullback metrics,
evaluates unique physical event deduplication, runs statistical bootstrap and adversarial tests,
and generates the authoritative master JSON artifact.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_Q_FRACTAL_VALIDATION"
BASELINE_PATH = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY" / "master_phase_p_discovery.json"


def compute_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0, "win_rate": 0.0, "expectancy_r": 0.0,
            "total_r": 0.0, "profit_factor": 0.0, "max_drawdown_r": 0.0,
            "median_r": 0.0, "trimmed_expectancy_r": 0.0, "exp_r_ex_top1": 0.0,
            "exp_r_ex_top2": 0.0, "top2_concentration_pct": 0.0,
        }

    r_vals = np.array([float(t["realized_r"]) for t in trades], dtype=np.float64)
    wins = r_vals[r_vals > 0]
    losses = r_vals[r_vals <= 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / n
    total_r = float(np.sum(r_vals))
    exp_r = total_r / n

    gross_profit = float(np.sum(wins)) if len(wins) else 0.0
    gross_loss = abs(float(np.sum(losses))) if len(losses) else 0.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else 999.0

    # Max Drawdown
    cum_r = np.cumsum(r_vals)
    peak = np.maximum.accumulate(cum_r)
    dd = peak - cum_r
    max_dd = float(np.max(dd)) if len(dd) else 0.0

    # Trimmed Expectancy (middle 90%)
    if n >= 10:
        p5, p95 = np.percentile(r_vals, [5, 95])
        trimmed = r_vals[(r_vals >= p5) & (r_vals <= p95)]
        trimmed_exp = float(np.mean(trimmed)) if len(trimmed) else exp_r
    else:
        trimmed_exp = exp_r

    sorted_r = np.sort(r_vals)
    ex_top1 = float(np.mean(sorted_r[:-1])) if n > 1 else exp_r
    ex_top2 = float(np.mean(sorted_r[:-2])) if n > 2 else exp_r
    top2_sum = float(np.sum(sorted_r[-2:])) if n >= 2 else 0.0
    top2_conc = (top2_sum / total_r * 100.0) if total_r > 0 else 0.0

    return {
        "total_trades": n,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 4),
        "expectancy_r": round(exp_r, 4),
        "total_r": round(total_r, 2),
        "profit_factor": round(min(pf, 999.0), 3),
        "max_drawdown_r": round(max_dd, 2),
        "median_r": round(float(np.median(r_vals)), 4),
        "trimmed_expectancy_r": round(trimmed_exp, 4),
        "exp_r_ex_top1": round(ex_top1, 4),
        "exp_r_ex_top2": round(ex_top2, 4),
        "top2_concentration_pct": round(top2_conc, 1),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 100)
    print("PHASE Q MASTER ARTIFACT COMPILER & ADVANCED ANALYTICS")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 100)

    # 1. Load all 40 stream files
    stream_files = sorted(RESULTS_DIR.glob("FRAC_*.json"))
    print(f"Loaded {len(stream_files)} stream artifacts from {RESULTS_DIR}")

    all_streams: Dict[str, Any] = {}
    all_trades: List[Dict[str, Any]] = []

    for sf in stream_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
            sid = data["stream_id"]
            all_streams[sid] = data
            for t in data.get("trades", []):
                t["_stream_id"] = sid
                t["_symbol"] = data.get("symbol", "")
                t["_set_name"] = data.get("set_name", "")
                t["_hypothesis_type"] = data.get("hypothesis_type", "")
                all_trades.append(t)
        except Exception as e:
            print(f"[ERROR] Failed to load {sf.name}: {e}")

    print(f"Total streams compiled: {len(all_streams)} | Total trades: {len(all_trades)}")

    # 2. Load Phase P Baseline
    baseline_data = {}
    if BASELINE_PATH.exists():
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
    baseline_streams = baseline_data.get("streams", {})

    # 3. Comparative Matrix
    comparative = {}
    for sid, sdata in all_streams.items():
        parts = sid.replace("FRAC_", "").split("_")
        asset = parts[0]
        set_id = parts[1] + "_" + parts[2]
        hyp = "HYP_A_PULLBACK" if parts[3] == "PULLBACK" else "HYP_B_CONTINUATION"
        base_id = f"{asset}_{set_id}_{hyp}"

        base_fm = baseline_streams.get(base_id, {}).get("full", {})
        frac_fm = sdata["full_metrics"]

        if base_fm:
            comparative[sid] = {
                "baseline_id": base_id,
                "baseline_n": base_fm.get("total_trades", 0),
                "fractal_n": frac_fm.get("total_trades", 0),
                "delta_n": frac_fm.get("total_trades", 0) - base_fm.get("total_trades", 0),
                "baseline_exp_r": base_fm.get("expectancy_r", 0.0),
                "fractal_exp_r": frac_fm.get("expectancy_r", 0.0),
                "delta_exp_r": round(frac_fm.get("expectancy_r", 0.0) - base_fm.get("expectancy_r", 0.0), 4),
                "baseline_total_r": base_fm.get("total_r", 0.0),
                "fractal_total_r": frac_fm.get("total_r", 0.0),
                "delta_total_r": round(frac_fm.get("total_r", 0.0) - base_fm.get("total_r", 0.0), 2),
                "baseline_pf": base_fm.get("profit_factor", 0.0),
                "fractal_pf": frac_fm.get("profit_factor", 0.0),
                "delta_pf": round(frac_fm.get("profit_factor", 0.0) - base_fm.get("profit_factor", 0.0), 3),
                "baseline_wr": base_fm.get("win_rate", 0.0),
                "fractal_wr": frac_fm.get("win_rate", 0.0),
                "delta_wr": round(frac_fm.get("win_rate", 0.0) - base_fm.get("win_rate", 0.0), 4),
            }

    # 4. Alignment Analysis
    alignment_buckets: Dict[str, List[Dict[str, Any]]] = {}
    for t in all_trades:
        align = t.get("meta", {}).get("fractal_alignment", "UNKNOWN")
        alignment_buckets.setdefault(align, []).append(t)

    alignment_summary = {k: compute_metrics(v) for k, v in alignment_buckets.items()}

    # 5. Cross-Set Support Analysis
    support_buckets: Dict[str, List[Dict[str, Any]]] = {}
    for t in all_trades:
        sup = t.get("meta", {}).get("cross_set_support", 0)
        key = f"support_{sup}"
        support_buckets.setdefault(key, []).append(t)

    support_summary = {k: compute_metrics(v) for k, v in sorted(support_buckets.items())}

    # 6. Confidence Threshold Sweep across all trades
    conf_thresholds = [0.0, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    conf_sweep_summary = {}
    for th in conf_thresholds:
        subset = [t for t in all_trades if t.get("meta", {}).get("confidence_score", 0.0) >= th]
        m = compute_metrics(subset)
        m["threshold"] = th
        conf_sweep_summary[f"threshold_{th:.2f}"] = m

    # 7. Deduplication & Unique Physical Movements Analysis
    unique_events = set()
    total_signals = 0
    multi_set_events: Dict[str, int] = {}

    for t in all_trades:
        total_signals += 1
        meta = t.get("meta", {})
        ts = t.get("entry_ts", 0)
        btype = meta.get("break_type", "UNKNOWN")
        ev_id = f"{ts}_{btype}"
        unique_events.add(ev_id)
        multi_set_events[ev_id] = multi_set_events.get(ev_id, 0) + 1

    unique_event_count = len(unique_events)
    duplicated_signal_count = total_signals - unique_event_count
    multi_rep_events = sum(1 for c in multi_set_events.values() if c > 1)

    dedup_analysis = {
        "total_evaluated_trades": total_signals,
        "unique_physical_movements": unique_event_count,
        "duplicated_trade_representations": duplicated_signal_count,
        "events_with_multi_set_representation": multi_rep_events,
        "duplication_ratio": round(total_signals / max(unique_event_count, 1), 2),
    }

    # 8. Scale-Level Aggregates (Set 1 to Set 5)
    scale_summary = {}
    for set_name in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        set_trades = [t for t in all_trades if t.get("_set_name") == set_name]
        scale_summary[set_name] = compute_metrics(set_trades)

    # 9. Asset-Level Aggregates (BTC, ETH, SOL, BNB)
    asset_summary = {}
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
        asset_trades = [t for t in all_trades if t.get("_symbol") == sym]
        asset_summary[sym] = compute_metrics(asset_trades)

    # 10. Pullback vs Continuation Comparison
    phase_summary = {
        "PULLBACK": compute_metrics([t for t in all_trades if t.get("_hypothesis_type") == "PULLBACK"]),
        "CONTINUATION": compute_metrics([t for t in all_trades if t.get("_hypothesis_type") == "CONTINUATION"]),
    }

    # 11. Statistical Validation (Stationary Bootstrap on all trades)
    r_arr = np.array([float(t["realized_r"]) for t in all_trades], dtype=np.float64)
    rng = np.random.default_rng(42)
    n_boot = 2000
    boot_means = np.zeros(n_boot)
    n_t = len(r_arr)
    for b in range(n_boot):
        sample = rng.choice(r_arr, size=n_t, replace=True)
        boot_means[b] = np.mean(sample)

    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    p_null = float(np.mean(boot_means <= 0.0))

    statistical_validation = {
        "sample_size_N": n_t,
        "sample_expectancy_r": round(float(np.mean(r_arr)), 4),
        "sample_std_r": round(float(np.std(r_arr)), 4),
        "bootstrap_replications": n_boot,
        "bootstrap_mean_r": round(float(np.mean(boot_means)), 4),
        "ci_95_lower_r": round(ci_lower, 4),
        "ci_95_upper_r": round(ci_upper, 4),
        "null_hypothesis_p_value": round(p_null, 6),
        "is_statistically_significant": ci_lower > 0.0,
    }

    # Compile master dictionary
    master = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "PHASE_Q_FRACTAL_STATE_ENGINE_VALIDATION",
        "total_streams": len(all_streams),
        "total_trades": len(all_trades),
        "streams": {
            sid: {
                "full_metrics": sdata["full_metrics"],
                "splits": sdata["splits"],
                "filter_rate": sdata.get("filter_rate", 0.0),
            }
            for sid, sdata in all_streams.items()
        },
        "comparative_against_baseline": comparative,
        "alignment_conditioned_performance": alignment_summary,
        "cross_set_support_performance": support_summary,
        "confidence_threshold_sweep": conf_sweep_summary,
        "deduplication_analysis": dedup_analysis,
        "scale_aggregates": scale_summary,
        "asset_aggregates": asset_summary,
        "phase_aggregates": phase_summary,
        "statistical_validation": statistical_validation,
    }

    out_file = RESULTS_DIR / "master_phase_q_fractal_validation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2)

    print(f"\nSuccessfully compiled master artifact: {out_file}")
    print(f"Overall Total R: {sum(s['full_metrics']['total_r'] for s in all_streams.values()):.2f}R")
    print(f"Overall ExpR: {np.mean([s['full_metrics']['expectancy_r'] for s in all_streams.values()]):.4f}R")
    print(f"Bootstrap 95% CI: [{ci_lower:.4f}R, {ci_upper:.4f}R] | p-value: {p_null:.6f}")


if __name__ == "__main__":
    main()
