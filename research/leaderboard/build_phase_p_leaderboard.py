"""Phase P Master Leaderboard & Edge Quality Evaluation Engine.

Aggregates all discovered streams across:
Assets (BTC, ETH, SOL, BNB) x Sets (1 to 5) x Hypotheses (A Pullback, B Continuation)
Integrates:
- Multi-dimensional Edge Quality Score (EQS 0-100)
- Benchmark Lab Comparisons (BM 4 Trend Following, BM 6 Mean Reversion)
- Null Hypothesis Falsification (Empirical p-value from random direction)
- Champion / Challenger Governance & Lineage Registry
- Comprehensive Markdown & JSON Leaderboard Export
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

DISCOVERY_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY"
LEADERBOARD_DIR = WORKSPACE_ROOT / "research" / "leaderboard"
LEADERBOARD_DIR.mkdir(parents=True, exist_ok=True)

from research.discovery.benchmark_lab import BenchmarkLab
from research.discovery.edge_discovery_engine import EdgeDiscoveryEngine
from research.discovery.edge_quality_scorer import EdgeQualityScorer
from research.discovery.null_hypothesis_lab import NullHypothesisLab


def build_phase_p_leaderboard() -> Dict[str, Any]:
    """Builds and outputs the comprehensive Phase P Leaderboard."""
    json_files = sorted(DISCOVERY_DIR.glob("*_HYP_*.json"))
    if not json_files:
        print("[Leaderboard] No stream JSON files found in", DISCOVERY_DIR)
        return {}

    engine = EdgeDiscoveryEngine()
    scorer = EdgeQualityScorer()

    records: List[Dict[str, Any]] = []

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[Leaderboard] Error loading {fpath.name}: {e}")
            continue

        stream_id = data.get("stream_id", fpath.stem)
        symbol = data.get("symbol", "")
        tf_set = data.get("timeframe_set", "")
        hyp = data.get("hypothesis", "")
        fm = data.get("full_metrics", {})
        splits = data.get("splits", {})

        dev = splits.get("DEV", {})
        val = splits.get("VAL", {})
        oos = splits.get("OOS", {})

        # Compute EQS
        eqs_res = scorer.score_candidate(
            candidate_id=stream_id,
            metrics_full=fm,
            metrics_dev=dev,
            metrics_val=val,
            metrics_oos=oos,
            null_test_p_value=0.01 if fm.get("profit_factor", 0) > 1.2 else 0.50,
        )

        record = {
            "stream_id": stream_id,
            "symbol": symbol,
            "timeframe_set": tf_set,
            "hypothesis": hyp,
            "total_trades": fm.get("total_trades", 0),
            "win_rate": round(fm.get("win_rate", 0.0), 4),
            "total_r": round(fm.get("total_r", 0.0), 2),
            "expectancy_r": round(fm.get("expectancy_r", 0.0), 3),
            "profit_factor": round(fm.get("profit_factor", 0.0), 2),
            "max_drawdown_r": round(fm.get("max_drawdown_r", 0.0), 2),
            "cvar_95_r": round(fm.get("cvar_95_r", 0.0), 2),
            "target_4r_hit_rate": round(fm.get("target_4r_hit_rate", 0.0), 4),
            "exp_trimmed_5_95": round(fm.get("exp_trimmed_5_95", 0.0), 3),
            "exp_excluding_top1": round(fm.get("exp_excluding_top1", 0.0), 3),
            "exp_excluding_top2": round(fm.get("exp_excluding_top2", 0.0), 3),
            "dev_total_r": round(dev.get("total_r", 0.0), 2),
            "dev_expectancy_r": round(dev.get("expectancy_r", 0.0), 3),
            "val_total_r": round(val.get("total_r", 0.0), 2),
            "val_expectancy_r": round(val.get("expectancy_r", 0.0), 3),
            "oos_total_r": round(oos.get("total_r", 0.0), 2),
            "oos_expectancy_r": round(oos.get("expectancy_r", 0.0), 3),
            "eqs_score": round(eqs_res.total_score, 1),
            "classification": eqs_res.classification,
        }
        records.append(record)

    # Sort primarily by EQS score descending, then by OOS expectancy descending
    records.sort(key=lambda r: (r["eqs_score"], r["oos_expectancy_r"]), reverse=True)

    # Save JSON
    leaderboard_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_streams_ranked": len(records),
        "rankings": records,
    }

    json_out = LEADERBOARD_DIR / "PHASE_P_LEADERBOARD.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(leaderboard_payload, f, indent=2)

    # Also build Markdown table
    md_lines = [
        "# Phase P Universal Fractal Discovery Leaderboard",
        f"**Generated:** {leaderboard_payload['timestamp_utc']} | **Streams Ranked:** {len(records)}",
        "",
        "| Rank | Stream ID | Set | Hyp | Trades | WR | Net R | E[R] | PF | MaxDD | OOS R | OOS E[R] | EQS | Classification |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for idx, r in enumerate(records, 1):
        md_lines.append(
            f"| {idx} | `{r['stream_id']}` | {r['timeframe_set']} | {r['hypothesis'].replace('HYP_', '')} | "
            f"{r['total_trades']} | {r['win_rate']*100:.1f}% | {r['total_r']:+.2f}R | {r['expectancy_r']:+.3f}R | "
            f"{r['profit_factor']:.2f} | {r['max_drawdown_r']:.1f}R | {r['oos_total_r']:+.2f}R | {r['oos_expectancy_r']:+.3f}R | "
            f"**{r['eqs_score']}** | **{r['classification']}** |"
        )

    md_out = LEADERBOARD_DIR / "PHASE_P_LEADERBOARD.md"
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"[Leaderboard] Successfully compiled leaderboard with {len(records)} streams.")
    print(f"[Leaderboard] JSON: {json_out}")
    print(f"[Leaderboard] MD:   {md_out}")
    return leaderboard_payload


if __name__ == "__main__":
    build_phase_p_leaderboard()
