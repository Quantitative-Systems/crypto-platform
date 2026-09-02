"""
Product 04 — Research Laboratory: Regime Attribution Analyzer
Executes Objective 6 of the Master Research Directive.

Partitions H1 trades across causal market regimes:
1. Trend: BULL_TREND, BEAR_TREND, RANGE_CHOP
2. Volatility: HIGH_VOLATILITY, NORMAL_VOLATILITY, COMPRESSION
3. Market Phase: EXPANSION, PULLBACK, REVERSAL/TRANSITION
"""

import os
import json
import glob
from typing import Dict, List, Any
from collections import defaultdict


def run_regime_attribution(results_dir: str) -> Dict[str, Any]:
    stream_files = glob.glob(os.path.join(results_dir, "*_SET_*.json"))
    
    all_trades: List[Dict[str, Any]] = []
    for fpath in stream_files:
        if "MASTER_SUMMARY" in fpath or "manifest" in fpath:
            continue
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
            trades = data.get("trades", [])
            stream_key = data.get("provenance", {}).get("stream_key", os.path.basename(fpath).replace(".json", ""))
            for t in trades:
                t["_stream_key"] = stream_key
                all_trades.append(t)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    # Regime categorization helpers
    def classify_regimes(trade: Dict[str, Any]) -> Dict[str, str]:
        prov = trade.get("metadata", {}).get("structural_provenance", {}) or {}
        htf_macro = str(prov.get("htf_macro_direction", trade.get("trend_regime", "RANGE"))).upper()
        htf_phase = str(prov.get("htf_phase", trade.get("market_phase", "CONTINUATION"))).upper()
        
        # Trend
        if "BULL" in htf_macro:
            trend = "BULL_TREND"
        elif "BEAR" in htf_macro:
            trend = "BEAR_TREND"
        else:
            trend = "RANGE_CHOP"
            
        # Phase
        if "EXPANSION" in htf_phase or "CONTINUATION" in htf_phase:
            phase = "EXPANSION_CONTINUATION"
        elif "PULLBACK" in htf_phase or "RETRACEMENT" in htf_phase:
            phase = "PULLBACK_RETRACEMENT"
        else:
            phase = "TRANSITION_REVERSAL"
            
        # Volatility
        vol = str(trade.get("volatility_regime", "NORMAL_VOLATILITY")).upper()
        if "HIGH" in vol:
            vol_class = "HIGH_VOLATILITY"
        elif "COMPRESSION" in vol or "LOW" in vol:
            vol_class = "COMPRESSION_LOW_VOL"
        else:
            vol_class = "NORMAL_VOLATILITY"
            
        return {"trend": trend, "phase": phase, "volatility": vol_class}

    trend_groups: Dict[str, List[float]] = defaultdict(list)
    phase_groups: Dict[str, List[float]] = defaultdict(list)
    vol_groups: Dict[str, List[float]] = defaultdict(list)

    for t in all_trades:
        r = t.get("realized_rr", t.get("net_r", 0.0))
        reg = classify_regimes(t)
        trend_groups[reg["trend"]].append(r)
        phase_groups[reg["phase"]].append(r)
        vol_groups[reg["volatility"]].append(r)

    def summarize_group(r_list: List[float]) -> Dict[str, Any]:
        if not r_list:
            return {"trades": 0, "net_r": 0.0, "mean_exp_r": 0.0, "win_rate_pct": 0.0}
        n = len(r_list)
        wins = sum(1 for x in r_list if x > 0)
        tot_r = sum(r_list)
        return {
            "trades": n,
            "wins": wins,
            "losses": n - wins,
            "win_rate_pct": round(wins / n * 100.0, 2),
            "net_r": round(tot_r, 4),
            "mean_exp_r": round(tot_r / n, 4)
        }

    report = {
        "total_trades_analyzed": len(all_trades),
        "trend_regimes": {k: summarize_group(v) for k, v in sorted(trend_groups.items())},
        "phase_regimes": {k: summarize_group(v) for k, v in sorted(phase_groups.items())},
        "volatility_regimes": {k: summarize_group(v) for k, v in sorted(vol_groups.items())}
    }

    return report


def main():
    results_dir = "/home/mrcn2/crypto-platform/research/results/BASELINE_002_20260902_013354"
    report = run_regime_attribution(results_dir)
    print("=" * 100)
    print("H1 REGIME ATTRIBUTION & PERFORMANCE MATRIX")
    print("=" * 100)
    print(json.dumps(report, indent=2))
    
    out_file = "/home/mrcn2/crypto-platform/scratch/regime_attribution_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Regime results written to: {out_file}")


if __name__ == "__main__":
    main()
