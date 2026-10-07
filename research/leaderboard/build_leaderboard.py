"""Research Leaderboard & Multi-Dimensional Edge Evaluation Engine.

Ranks strategy hypotheses using multi-dimensional criteria rather than raw returns:
1. OOS Expectancy & OOS Profit Factor
2. Trade Count & Statistical Validity (flags micro-sample anomalies)
3. Maximum Drawdown (R)
4. Cross-Period Stability (DEV vs VAL vs OOS consistency)
5. 4R Target Hit Rate
6. Cost Sensitivity & Economic Resilience

Also catalogs all failed hypotheses, diagnosing failure modes and preserving them permanently.
Outputs:
- research/leaderboard/RESEARCH_LEADERBOARD.json (and root RESEARCH_LEADERBOARD.json)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DISCOVERY_RESULTS_DIR = REPO_ROOT / "research" / "results" / "discovery"
LEADERBOARD_DIR = REPO_ROOT / "research" / "leaderboard"
LEADERBOARD_DIR.mkdir(parents=True, exist_ok=True)


def calculate_composite_score(record: Dict[str, Any]) -> float:
    """Calculate multi-dimensional score balancing edge strength, robustness, and stability."""
    m = record["overall_metrics"]
    wf = record["partitioned_walk_forward"]
    dev = wf["dev"]
    val = wf["val"]
    oos = wf["oos"]

    trades = m.get("trade_count", 0)
    if trades < 10:
        return -999.0  # Statistical significance penalty

    exp_r = m.get("expectancy_r", 0.0)
    oos_exp = oos.get("expectancy_r", 0.0)
    val_exp = val.get("expectancy_r", 0.0)
    dev_exp = dev.get("expectancy_r", 0.0)
    pf = m.get("profit_factor", 0.0)
    max_dd = max(m.get("max_drawdown_r", 1.0), 1.0)
    hit_4r = m.get("target_4r_hit_rate", 0.0)

    # Walk-forward consistency bonus / penalty
    wf_positive_count = sum(1 for e in (dev_exp, val_exp, oos_exp) if e > 0)

    # Base score: OOS expectancy weighted heavily
    score = (oos_exp * 40.0) + (exp_r * 20.0) + (min(pf, 5.0) * 10.0)
    # Trade sample scaling (log bonus up to ~100 trades)
    score += min(trades / 10.0, 10.0)
    # 4R hit bonus
    score += hit_4r * 15.0
    # Drawdown penalty
    score -= min(max_dd * 1.5, 30.0)
    # Walk-forward consistency bonus
    score += wf_positive_count * 10.0

    return round(score, 3)


def diagnose_failure_mode(record: Dict[str, Any]) -> str:
    """Diagnose why a strategy hypothesis failed to establish a robust edge."""
    m = record["overall_metrics"]
    wf = record["partitioned_walk_forward"]
    oos = wf["oos"]

    if m["trade_count"] < 10:
        return "INSUFFICIENT_OPPORTUNITY_FREQUENCY (Trade count < 10 across multi-year period)"
    if m["target_4r_hit_rate"] < 0.10:
        return "LOW_DESTINATION_REACHABILITY (Price rarely travels full 4R before structural stop/trailing)"
    if m["expectancy_r"] <= 0 and oos["expectancy_r"] <= 0:
        return "ZERO_PERSISTENT_EDGE (Loss rate and friction exceed gross win payoff across all periods)"
    if m["expectancy_r"] > 0 and oos["expectancy_r"] <= 0:
        return "OOS_REGIME_DEGRADATION (In-sample curve fit / failed to generalize to recent market regime)"
    if m["max_drawdown_r"] > 25.0:
        return "EXCESSIVE_DRAWDOWN_VOLATILITY (Drawdown > 25R during regime transitions)"
    return "COST_FRICTION_DRAG (Taker fees and slippage eroded marginal gross edge)"


def build_leaderboard() -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for path in sorted(DISCOVERY_RESULTS_DIR.glob("EXP_*.json")):
        try:
            with open(path, "r") as f:
                record = json.load(f)
            if record.get("status") != "COMPLETED":
                continue

            score = calculate_composite_score(record)
            m = record["overall_metrics"]
            oos = record["partitioned_walk_forward"]["oos"]

            entry = {
                "experiment_id": record["experiment_id"],
                "symbol": record["symbol"],
                "set_id": record["set_id"],
                "family_id": record["family_id"],
                "phase_mode": record["phase_mode"],
                "composite_score": score,
                "overall_expectancy_r": m["expectancy_r"],
                "oos_expectancy_r": oos["expectancy_r"],
                "total_r": m["total_r"],
                "profit_factor": m["profit_factor"],
                "trade_count": m["trade_count"],
                "win_rate": m["win_rate"],
                "max_drawdown_r": m["max_drawdown_r"],
                "target_4r_hit_rate": m["target_4r_hit_rate"],
                "is_qualified_candidate": (
                    m["trade_count"] >= 15
                    and m["expectancy_r"] > 0.0
                    and oos["expectancy_r"] > 0.0
                    and m["profit_factor"] >= 1.10
                ),
                "suspicious_flags": [],
            }

            if m["trade_count"] < 10 and m["total_r"] > 10.0:
                entry["suspicious_flags"].append("LOW_SAMPLE_HIGH_RETURN_ANOMALY")
            if m["expectancy_r"] > 0 and oos["expectancy_r"] < -0.30:
                entry["suspicious_flags"].append("EXTREME_OOS_DECAY")

            if entry["is_qualified_candidate"]:
                candidates.append(entry)
            else:
                entry["failure_mode"] = diagnose_failure_mode(record)
                failures.append(entry)

        except Exception as e:
            continue

    # Sort candidates by composite score descending
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    failures.sort(key=lambda x: x["composite_score"], reverse=True)

    leaderboard = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_evaluated_experiments": len(candidates) + len(failures),
            "qualified_edge_candidates_count": len(candidates),
            "rejected_failed_hypotheses_count": len(failures),
        },
        "qualified_candidates_leaderboard": candidates,
        "failed_hypotheses_registry": failures,
    }

    # Save to research/leaderboard/ and root
    with open(LEADERBOARD_DIR / "RESEARCH_LEADERBOARD.json", "w") as f:
        json.dump(leaderboard, f, indent=2)
    with open(REPO_ROOT / "RESEARCH_LEADERBOARD.json", "w") as f:
        json.dump(leaderboard, f, indent=2)

    print(f"Built RESEARCH_LEADERBOARD.json:")
    print(f" - Qualified Candidates: {len(candidates)}")
    print(f" - Failed Hypotheses: {len(failures)}")
    return leaderboard


if __name__ == "__main__":
    build_leaderboard()
