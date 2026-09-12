"""
Product 04 — Research Laboratory: Quantitative Performance Forensics Engine
Performs forensic quantitative decomposition on canonical replay results across 15 streams.

Computes:
1. Full historical data inventory
2. Reproducibility manifest
3. Canonical H0 vs ANCHOR_2 comparison
4. Complete Alpha Waterfall & Stage Survival Percentages
5. MFE -> Realized-R distributions (8 buckets & leakage analysis)
6. MAE forensics & cross-tabulations
7. Time-to-excursion forensics vs MTF bar duration & trailing latency
8. 4R target reality test (reach probabilities)
9. Exit / management attribution
10. Target provenance analysis (Weak Swing vs Structural Expansion)
11. Asset attribution (BTC, ETH, SOL)
12. Timeframe attribution (SET 1 to SET 5)
13. Market-regime diagnostics
14. Cost elasticity stress test (Base, +25%, +50%, +100%, +200%)
15. Trade dependency & event clustering
16. Ablation framework design
17. Statistical uncertainty & Monte Carlo framework design
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List

CACHE_DIR = "/home/mrcn2/crypto-platform/market_data/cache"
ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

TF_DURATIONS = {
    "1M": 30 * 86400,
    "1w": 7 * 86400,
    "1d": 86400,
    "4h": 4 * 3600,
    "1h": 3600,
    "15m": 900,
    "5m": 300,
    "1m": 60
}

TF_SET_INFO = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d", "label": "SET_1 (1M -> 1W -> 1D, Macro)"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h", "label": "SET_2 (1W -> 1D -> 4H, Position)"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h", "label": "SET_3 (1D -> 4H -> 1H, Swing)"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m", "label": "SET_4 (4H -> 1H -> 15M, Intraday)"},
    "SET_5": {"htf": "15m", "mtf": "5m", "ltf": "1m", "label": "SET_5 (15M -> 5M -> 1M, Scalp)"}
}


def audit_historical_data_inventory() -> Dict[str, Any]:
    """Audits data coverage for all assets and timeframes."""
    tfs = ["1M", "1w", "1d", "4h", "1h", "15m", "5m", "1m"]
    inventory = {}

    for asset in ASSETS:
        sym = f"{asset}USDT"
        inventory[asset] = {}
        for tf in tfs:
            fname = f"binance_{sym}_{tf}.json"
            fpath = os.path.join(CACHE_DIR, fname)
            if not os.path.exists(fpath):
                inventory[asset][tf] = {"status": "MISSING", "count": 0}
                continue

            with open(fpath, "r") as fp:
                bars = json.load(fp)

            count = len(bars)
            if count == 0:
                inventory[asset][tf] = {"status": "EMPTY", "count": 0}
                continue

            t0_ms = bars[0][0]
            t1_ms = bars[-1][0]
            t0_sec = t0_ms / 1000.0
            t1_sec = t1_ms / 1000.0

            dt_start = datetime.fromtimestamp(t0_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            dt_end = datetime.fromtimestamp(t1_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

            # Check duplicates & timestamp ordering
            dups = 0
            invalid_candles = 0
            seen_ts = set()
            exp_interval = TF_DURATIONS.get(tf, 3600) * 1000
            gaps = 0

            for idx, b in enumerate(bars):
                ts = b[0]
                if ts in seen_ts:
                    dups += 1
                seen_ts.add(ts)

                # Check OHLC validity
                op, hi, lo, cl = float(b[1]), float(b[2]), float(b[3]), float(b[4])
                if hi < lo or op <= 0 or cl <= 0 or hi <= 0 or lo <= 0:
                    invalid_candles += 1

                if idx > 0:
                    diff = ts - bars[idx-1][0]
                    if diff > exp_interval * 1.5:
                        gaps += 1

            # Check 2021-2022 coverage
            dev_start_ms = 1609459200000  # 2021-01-01 00:00:00 UTC
            dev_end_ms = 1672531199000    # 2022-12-31 23:59:59 UTC
            covers_dev = (t0_ms <= dev_start_ms) and (t1_ms >= dev_end_ms)

            inventory[asset][tf] = {
                "count": count,
                "start_utc": dt_start,
                "end_utc": dt_end,
                "covers_2021_2022": covers_dev,
                "duplicates": dups,
                "invalid_candles": invalid_candles,
                "gap_count": gaps,
                "timezone": "UTC (Binance Public API Standard)"
            }

    return inventory


def build_alpha_waterfall(stream_results: List[Dict[str, Any]], all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds the complete Alpha Waterfall:
    Market States -> HTF Qualified -> MTF Alignment -> MTF Setup -> MTF Retest ->
    LTF Trigger -> Target Resolved -> Risk Approved -> Executed -> Winners/Losses.
    """
    total_market_bars = sum(s.get("ltf_candles_count", 0) for s in stream_results)
    total_htf_states = sum(s.get("engine_runs", {}).get("htf", 0) for s in stream_results)
    total_mtf_states = sum(s.get("engine_runs", {}).get("mtf", 0) for s in stream_results)
    total_ltf_states = sum(s.get("engine_runs", {}).get("ltf", 0) for s in stream_results)

    # Aggregate candidate stages
    all_cands = []
    for s in stream_results:
        all_cands.extend(s.get("all_candidates", []))

    total_htf_qualified = len(all_cands)
    mtf_aligned_count = sum(1 for c in all_cands if "CandidateState.WAIT_MTF_RETEST" in c.get("stages_reached", []) or "WAIT_MTF_RETEST" in c.get("stages_reached", []))
    mtf_retest_count = sum(1 for c in all_cands if "CandidateState.WAIT_LTF_TRIGGER" in c.get("stages_reached", []) or "WAIT_LTF_TRIGGER" in c.get("stages_reached", []))
    ltf_trigger_count = sum(1 for c in all_cands if "CandidateState.RISK_GATE" in c.get("stages_reached", []) or "RISK_GATE" in c.get("stages_reached", []))
    target_resolved_count = sum(1 for c in all_cands if "CandidateState.ENTERED" in c.get("stages_reached", []) or "ENTERED" in c.get("stages_reached", []))
    
    executed_trades = len(all_trades)
    winning_trades = sum(1 for t in all_trades if float(t.get("realized_r", t.get("realized_rr", 0.0))) > 0.0)
    losing_trades = sum(1 for t in all_trades if float(t.get("realized_r", t.get("realized_rr", 0.0))) < 0.0)
    be_trades = sum(1 for t in all_trades if abs(float(t.get("realized_r", t.get("realized_rr", 0.0)))) < 1e-6)

    # Rejection attribution across candidates
    rejection_reasons = {}
    for c in all_cands:
        r = c.get("invalidation_reason")
        if r:
            rejection_reasons[r] = rejection_reasons.get(r, 0) + 1

    # Stage-to-stage survival percentages
    def pct(num, den):
        return round((num / den * 100.0), 2) if den > 0 else 0.0

    survival = {
        "market_bars_to_htf_qualified_pct": pct(total_htf_qualified, total_market_bars),
        "htf_to_mtf_alignment_survival_pct": pct(mtf_aligned_count, total_htf_qualified),
        "mtf_alignment_to_retest_survival_pct": pct(mtf_retest_count, mtf_aligned_count),
        "retest_to_ltf_trigger_survival_pct": pct(ltf_trigger_count, mtf_retest_count),
        "ltf_trigger_to_target_resolved_survival_pct": pct(target_resolved_count, ltf_trigger_count),
        "target_resolved_to_execution_survival_pct": pct(executed_trades, target_resolved_count),
        "execution_to_win_pct": pct(winning_trades, executed_trades)
    }

    return {
        "funnel_counts": {
            "total_market_bars": total_market_bars,
            "htf_state_runs": total_htf_states,
            "mtf_state_runs": total_mtf_states,
            "ltf_state_runs": total_ltf_states,
            "htf_qualified_candidates": total_htf_qualified,
            "mtf_aligned_candidates": mtf_aligned_count,
            "mtf_retested_candidates": mtf_retest_count,
            "ltf_triggered_candidates": ltf_trigger_count,
            "target_resolved_candidates": target_resolved_count,
            "executed_trades": executed_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "breakeven_trades": be_trades
        },
        "survival_rates": survival,
        "rejection_breakdown": rejection_reasons
    }


def analyze_mfe_realized_r(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes MFE -> Realized-R distributions across the 8 specified buckets:
    <0R, 0–0.5R, 0.5–1R, 1–1.5R, 1.5–2R, 2–3R, 3–4R, 4R+
    """
    buckets = {
        "<0R": [],
        "0-0.5R": [],
        "0.5-1R": [],
        "1-1.5R": [],
        "1.5-2R": [],
        "2-3R": [],
        "3-4R": [],
        "4R+": []
    }

    for t in all_trades:
        mfe = float(t.get("mfe_r", 0.0))
        if mfe < 0.0:
            buckets["<0R"].append(t)
        elif 0.0 <= mfe < 0.5:
            buckets["0-0.5R"].append(t)
        elif 0.5 <= mfe < 1.0:
            buckets["0.5-1R"].append(t)
        elif 1.0 <= mfe < 1.5:
            buckets["1-1.5R"].append(t)
        elif 1.5 <= mfe < 2.0:
            buckets["1.5-2R"].append(t)
        elif 2.0 <= mfe < 3.0:
            buckets["2-3R"].append(t)
        elif 3.0 <= mfe < 4.0:
            buckets["3-4R"].append(t)
        else:
            buckets["4R+"].append(t)

    bucket_stats = {}
    for b_name, b_trades in buckets.items():
        n = len(b_trades)
        if n == 0:
            bucket_stats[b_name] = {
                "count": 0, "pct_of_total": 0.0, "realized_r": 0.0,
                "expectancy": 0.0, "win_rate": 0.0, "exit_reasons": {}
            }
            continue

        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in b_trades]
        wins = [r for r in r_vals if r > 0.0]
        net_r = sum(r_vals)
        exp = net_r / n
        wr = len(wins) / n * 100.0

        exit_reasons = {}
        for t in b_trades:
            reason = t.get("exit_reason", "UNKNOWN")
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        bucket_stats[b_name] = {
            "count": n,
            "pct_of_total": round(n / len(all_trades) * 100.0, 2),
            "realized_r": round(net_r, 4),
            "expectancy": round(exp, 4),
            "win_rate": round(wr, 2),
            "exit_reasons": exit_reasons
        }

    # Leakage Identification
    mfe_ge_1r_loss = [t for t in all_trades if float(t.get("mfe_r", 0.0)) >= 1.0 and float(t.get("realized_r", t.get("realized_rr", 0.0))) <= -0.9]
    mfe_ge_2r_loss = [t for t in all_trades if float(t.get("mfe_r", 0.0)) >= 2.0 and float(t.get("realized_r", t.get("realized_rr", 0.0))) <= -0.9]
    mfe_ge_3r_loss = [t for t in all_trades if float(t.get("mfe_r", 0.0)) >= 3.0 and float(t.get("realized_r", t.get("realized_rr", 0.0))) <= -0.9]
    reached_4r = [t for t in all_trades if float(t.get("mfe_r", 0.0)) >= 4.0]
    reached_target = [t for t in all_trades if t.get("exit_reason") == "HTF_TP"]
    mtf_trail_exits = [t for t in all_trades if t.get("exit_reason") == "MTF_STRUCTURAL_TRAIL"]

    # MFE Capture Ratio (Realized R / MFE) for winning trades
    win_trades = [t for t in all_trades if float(t.get("realized_r", t.get("realized_rr", 0.0))) > 0.0]
    capture_ratios = []
    for t in win_trades:
        mfe = float(t.get("mfe_r", 0.0))
        real_r = float(t.get("realized_r", t.get("realized_rr", 0.0)))
        if mfe > 0.0:
            capture_ratios.append(real_r / mfe)
    avg_capture_ratio = round(float(np.mean(capture_ratios)), 4) if capture_ratios else 0.0

    return {
        "bucket_stats": bucket_stats,
        "leakage_summary": {
            "mfe_ge_1r_ending_in_full_loss": len(mfe_ge_1r_loss),
            "mfe_ge_2r_ending_in_full_loss": len(mfe_ge_2r_loss),
            "mfe_ge_3r_ending_in_full_loss": len(mfe_ge_3r_loss),
            "trades_reaching_ge_4r": len(reached_4r),
            "trades_reaching_target": len(reached_target),
            "trades_exited_by_mtf_trail": len(mtf_trail_exits),
            "average_mfe_capture_ratio_winners": avg_capture_ratio
        }
    }


def analyze_mae_forensics(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cross-tabulates MAE vs MFE, Realized R, and Exit Reason."""
    mae_buckets = {
        "0-0.2R": [],
        "0.2-0.5R": [],
        "0.5-0.8R": [],
        "0.8-1.0R": [],
        "1.0R+": []
    }

    for t in all_trades:
        mae = float(t.get("mae_r", 0.0))
        if mae < 0.2:
            mae_buckets["0-0.2R"].append(t)
        elif 0.2 <= mae < 0.5:
            mae_buckets["0.2-0.5R"].append(t)
        elif 0.5 <= mae < 0.8:
            mae_buckets["0.5-0.8R"].append(t)
        elif 0.8 <= mae < 1.0:
            mae_buckets["0.8-1.0R"].append(t)
        else:
            mae_buckets["1.0R+"].append(t)

    mae_stats = {}
    for b_name, b_trades in mae_buckets.items():
        n = len(b_trades)
        if n == 0:
            mae_stats[b_name] = {
                "count": 0, "avg_mfe_r": 0.0, "avg_realized_r": 0.0,
                "win_rate": 0.0, "exit_reasons": {}
            }
            continue

        mfe_vals = [float(t.get("mfe_r", 0.0)) for t in b_trades]
        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in b_trades]
        wins = [r for r in r_vals if r > 0.0]

        exits = {}
        for t in b_trades:
            reason = t.get("exit_reason", "UNKNOWN")
            exits[reason] = exits.get(reason, 0) + 1

        mae_stats[b_name] = {
            "count": n,
            "avg_mfe_r": round(float(np.mean(mfe_vals)), 4),
            "avg_realized_r": round(float(np.mean(r_vals)), 4),
            "win_rate": round(len(wins) / n * 100.0, 2),
            "exit_reasons": exits
        }

    return mae_stats


def analyze_time_to_excursion(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes median time to milestones (+0.5R, +1R, +2R, +3R, MFE, stop, target)
    across timeframe sets and compares with MTF bar duration.
    """
    tf_groups = {}
    for t in all_trades:
        tf = t.get("timeframe_set", "UNKNOWN")
        tf_groups.setdefault(tf, []).append(t)

    tf_timing = {}
    for tf, trades in tf_groups.items():
        meta_list = [t.get("metadata", {}) for t in trades]
        
        t_0_5r = [m["time_to_0_5r"] for m in meta_list if "time_to_0_5r" in m]
        t_1_0r = [m["time_to_1_0r"] for m in meta_list if "time_to_1_0r" in m]
        t_2_0r = [m["time_to_2_0r"] for m in meta_list if "time_to_2_0r" in m]
        t_3_0r = [m["time_to_3_0r"] for m in meta_list if "time_to_3_0r" in m]
        t_mfe = [m["time_to_mfe"] for m in meta_list if "time_to_mfe" in m]
        t_stop = [m["time_to_stop"] for m in meta_list if "time_to_stop" in m]
        t_target = [m["time_to_target"] for m in meta_list if "time_to_target" in m]

        # MTF bar duration in seconds
        mtf_str = TF_SET_INFO.get(tf, {}).get("mtf", "1h")
        mtf_bar_sec = TF_DURATIONS.get(mtf_str, 3600)

        tf_timing[tf] = {
            "n_trades": len(trades),
            "mtf_bar_duration_sec": mtf_bar_sec,
            "mtf_bar_duration_hours": round(mtf_bar_sec / 3600.0, 2),
            "median_time_to_0_5r_hours": round(float(np.median(t_0_5r)) / 3600.0, 2) if t_0_5r else None,
            "median_time_to_1_0r_hours": round(float(np.median(t_1_0r)) / 3600.0, 2) if t_1_0r else None,
            "median_time_to_2_0r_hours": round(float(np.median(t_2_0r)) / 3600.0, 2) if t_2_0r else None,
            "median_time_to_3_0r_hours": round(float(np.median(t_3_0r)) / 3600.0, 2) if t_3_0r else None,
            "median_time_to_mfe_hours": round(float(np.median(t_mfe)) / 3600.0, 2) if t_mfe else None,
            "median_time_to_stop_hours": round(float(np.median(t_stop)) / 3600.0, 2) if t_stop else None,
            "median_time_to_target_hours": round(float(np.median(t_target)) / 3600.0, 2) if t_target else None,
        }

    return tf_timing


def test_4r_target_reality(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tests reach probability for candidates with planned RR >= 4.0."""
    ge_4r_trades = [t for t in all_trades if float(t.get("raw_rr", t.get("planned_rr", 0.0))) >= 4.0]
    total_4r = len(ge_4r_trades)

    if total_4r == 0:
        return {
            "total_planned_4r_trades": 0,
            "p_reach_0_5r": 0.0, "p_reach_1_0r": 0.0, "p_reach_2_0r": 0.0,
            "p_reach_3_0r": 0.0, "p_reach_4_0r": 0.0, "p_reach_target": 0.0
        }

    reach_0_5r = sum(1 for t in ge_4r_trades if float(t.get("mfe_r", 0.0)) >= 0.5)
    reach_1_0r = sum(1 for t in ge_4r_trades if float(t.get("mfe_r", 0.0)) >= 1.0)
    reach_2_0r = sum(1 for t in ge_4r_trades if float(t.get("mfe_r", 0.0)) >= 2.0)
    reach_3_0r = sum(1 for t in ge_4r_trades if float(t.get("mfe_r", 0.0)) >= 3.0)
    reach_4_0r = sum(1 for t in ge_4r_trades if float(t.get("mfe_r", 0.0)) >= 4.0)
    reach_target = sum(1 for t in ge_4r_trades if t.get("exit_reason") == "HTF_TP")

    return {
        "total_planned_4r_trades": total_4r,
        "p_reach_0_5r": round(reach_0_5r / total_4r * 100.0, 2),
        "p_reach_1_0r": round(reach_1_0r / total_4r * 100.0, 2),
        "p_reach_2_0r": round(reach_2_0r / total_4r * 100.0, 2),
        "p_reach_3_0r": round(reach_3_0r / total_4r * 100.0, 2),
        "p_reach_4_0r": round(reach_4_0r / total_4r * 100.0, 2),
        "p_reach_target": round(reach_target / total_4r * 100.0, 2),
        "verdict": (
            "FREQUENTLY_ACHIEVABLE" if (reach_4_0r / total_4r >= 0.25) else
            ("RARE_BUT_STRUCTURAL" if (reach_4_0r / total_4r >= 0.05) else "USUALLY_UNREACHABLE")
        )
    }


def analyze_exit_attribution(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Decomposes economic contribution by exit mechanism."""
    exit_groups = {
        "INITIAL_LTF_SL": [],
        "MTF_TRAIL_LOSS": [],
        "MTF_TRAIL_BREAKEVEN": [],
        "MTF_TRAIL_PROFIT": [],
        "HTF_TARGET": [],
        "EMERGENCY": []
    }

    for t in all_trades:
        reason = t.get("exit_reason", "UNKNOWN")
        r_val = float(t.get("realized_r", t.get("realized_rr", 0.0)))
        
        if reason == "INITIAL_LTF_SL":
            exit_groups["INITIAL_LTF_SL"].append(t)
        elif reason == "MTF_STRUCTURAL_TRAIL":
            if r_val > 0.1:
                exit_groups["MTF_TRAIL_PROFIT"].append(t)
            elif abs(r_val) <= 0.1:
                exit_groups["MTF_TRAIL_BREAKEVEN"].append(t)
            else:
                exit_groups["MTF_TRAIL_LOSS"].append(t)
        elif reason == "HTF_TP":
            exit_groups["HTF_TARGET"].append(t)
        else:
            exit_groups["EMERGENCY"].append(t)

    attribution = {}
    for e_name, e_trades in exit_groups.items():
        n = len(e_trades)
        if n == 0:
            attribution[e_name] = {
                "count": 0, "net_r": 0.0, "expectancy": 0.0,
                "avg_mfe": 0.0, "avg_mae": 0.0
            }
            continue

        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in e_trades]
        mfe_vals = [float(t.get("mfe_r", 0.0)) for t in e_trades]
        mae_vals = [float(t.get("mae_r", 0.0)) for t in e_trades]

        attribution[e_name] = {
            "count": n,
            "net_r": round(sum(r_vals), 4),
            "expectancy": round(sum(r_vals) / n, 4),
            "avg_mfe": round(float(np.mean(mfe_vals)), 4),
            "avg_mae": round(float(np.mean(mae_vals)), 4)
        }

    return attribution


def analyze_target_provenance(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Separates trades by HTF_WEAK_SWING vs FORWARD_STRUCTURAL_EXPANSION."""
    provenance_groups = {
        "HTF_WEAK_SWING": [],
        "FORWARD_STRUCTURAL_EXPANSION": [],
        "LIQUIDITY_POOL": [],
        "OPPOSING_KEYZONE": [],
        "OTHER": []
    }

    for t in all_trades:
        prov = t.get("metadata", {}).get("structural_provenance", {})
        prov_type = prov.get("htf_target_provenance") or "OTHER"
        if prov_type in provenance_groups:
            provenance_groups[prov_type].append(t)
        else:
            provenance_groups["OTHER"].append(t)

    result = {}
    for p_name, p_trades in provenance_groups.items():
        n = len(p_trades)
        if n == 0:
            continue
        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in p_trades]
        wins = [r for r in r_vals if r > 0.0]
        result[p_name] = {
            "count": n,
            "net_r": round(sum(r_vals), 4),
            "expectancy": round(sum(r_vals) / n, 4),
            "win_rate": round(len(wins) / n * 100.0, 2),
            "avg_mfe_r": round(float(np.mean([float(t.get("mfe_r", 0.0)) for t in p_trades])), 4),
            "avg_mae_r": round(float(np.mean([float(t.get("mae_r", 0.0)) for t in p_trades])), 4)
        }
    return result


def analyze_asset_attribution(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Decomposes performance across BTC, ETH, and SOL."""
    asset_groups = {a: [] for a in ASSETS}
    for t in all_trades:
        sym = t.get("symbol", "")
        for a in ASSETS:
            if a in sym:
                asset_groups[a].append(t)
                break

    result = {}
    for a, a_trades in asset_groups.items():
        n = len(a_trades)
        if n == 0:
            result[a] = {"count": 0, "net_r": 0.0, "expectancy": 0.0, "pf": 0.0, "win_rate": 0.0}
            continue
        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in a_trades]
        wins = [r for r in r_vals if r > 0.0]
        losses = [r for r in r_vals if r < 0.0]
        win_sum = sum(wins)
        loss_sum = abs(sum(losses))
        pf = (win_sum / loss_sum) if loss_sum > 0 else (999.0 if win_sum > 0 else 0.0)

        result[a] = {
            "count": n,
            "net_r": round(sum(r_vals), 4),
            "expectancy": round(sum(r_vals) / n, 4),
            "pf": round(pf, 4),
            "win_rate": round(len(wins) / n * 100.0, 2),
            "avg_mfe_r": round(float(np.mean([float(t.get("mfe_r", 0.0)) for t in a_trades])), 4),
            "avg_mae_r": round(float(np.mean([float(t.get("mae_r", 0.0)) for t in a_trades])), 4)
        }
    return result


def analyze_timeframe_attribution(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Decomposes performance across SET 1 to SET 5."""
    tf_groups = {s: [] for s in TF_SETS}
    for t in all_trades:
        tf = t.get("timeframe_set", "")
        if tf in tf_groups:
            tf_groups[tf].append(t)

    result = {}
    for s, s_trades in tf_groups.items():
        n = len(s_trades)
        if n == 0:
            result[s] = {"count": 0, "net_r": 0.0, "expectancy": 0.0, "pf": 0.0, "win_rate": 0.0}
            continue
        r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in s_trades]
        wins = [r for r in r_vals if r > 0.0]
        losses = [r for r in r_vals if r < 0.0]
        win_sum = sum(wins)
        loss_sum = abs(sum(losses))
        pf = (win_sum / loss_sum) if loss_sum > 0 else (999.0 if win_sum > 0 else 0.0)

        result[s] = {
            "count": n,
            "net_r": round(sum(r_vals), 4),
            "expectancy": round(sum(r_vals) / n, 4),
            "pf": round(pf, 4),
            "win_rate": round(len(wins) / n * 100.0, 2),
            "avg_mfe_r": round(float(np.mean([float(t.get("mfe_r", 0.0)) for t in s_trades])), 4),
            "avg_mae_r": round(float(np.mean([float(t.get("mae_r", 0.0)) for t in s_trades])), 4)
        }
    return result


def analyze_regime_diagnostics(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Classifies trades by trend, volatility, and phase regimes."""
    trend_groups = {}
    vol_groups = {}
    phase_groups = {}

    for t in all_trades:
        tr = t.get("trend_regime", "RANGE_CHOP")
        vol = t.get("volatility_regime", "NORMAL_VOLATILITY")
        ph = t.get("market_phase", "CONTINUATION")

        trend_groups.setdefault(tr, []).append(t)
        vol_groups.setdefault(vol, []).append(t)
        phase_groups.setdefault(ph, []).append(t)

    def summarize(groups):
        out = {}
        for k, tr_list in groups.items():
            n = len(tr_list)
            r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in tr_list]
            wins = [r for r in r_vals if r > 0.0]
            losses = [r for r in r_vals if r < 0.0]
            pf = (sum(wins) / abs(sum(losses))) if losses and abs(sum(losses)) > 0 else (999.0 if wins else 0.0)
            out[k] = {
                "count": n,
                "net_r": round(sum(r_vals), 4),
                "expectancy": round(sum(r_vals) / n, 4) if n > 0 else 0.0,
                "win_rate": round(len(wins) / n * 100.0, 2) if n > 0 else 0.0,
                "pf": round(pf, 4)
            }
        return out

    return {
        "trend_regimes": summarize(trend_groups),
        "volatility_regimes": summarize(vol_groups),
        "phase_regimes": summarize(phase_groups)
    }


def analyze_cost_elasticity(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates sensitivity to Base, +25%, +50%, +100%, +200% friction."""
    stress_multipliers = [1.0, 1.25, 1.50, 2.00, 3.00]
    labels = ["Base Cost", "+25% Cost", "+50% Cost", "+100% Cost", "+200% Cost"]

    elasticity = {}
    for mult, label in zip(stress_multipliers, labels):
        stressed_net_r = []
        for t in all_trades:
            gross_r = float(t.get("gross_r", 0.0))
            fees_r = float(t.get("fees_r", 0.0))
            slippage_r = float(t.get("slippage_r", 0.0))
            funding_r = float(t.get("funding_r", 0.0))
            
            stressed_friction = (fees_r + slippage_r + funding_r) * mult
            stressed_net = gross_r - stressed_friction
            stressed_net_r.append(stressed_net)

        n = len(stressed_net_r)
        net_sum = sum(stressed_net_r)
        exp = net_sum / n if n > 0 else 0.0
        wins = [r for r in stressed_net_r if r > 0.0]
        losses = [r for r in stressed_net_r if r < 0.0]
        pf = (sum(wins) / abs(sum(losses))) if losses and abs(sum(losses)) > 0 else (999.0 if wins else 0.0)

        elasticity[label] = {
            "multiplier": mult,
            "net_r": round(net_sum, 4),
            "expectancy": round(exp, 4),
            "profit_factor": round(pf, 4)
        }

    return elasticity


def analyze_trade_dependency(all_trades: List[Dict[str, Any]], window_seconds: int = 86400) -> Dict[str, Any]:
    """Identifies overlapping concurrent trades caused by broad market events."""
    n_raw = len(all_trades)
    if n_raw == 0:
        return {"raw_trades": 0, "unique_setups": 0, "overlapping_events": 0, "event_clusters": 0}

    # Unique setup keys
    setup_keys = set()
    for t in all_trades:
        key = (t.get("symbol"), t.get("entry_price"), t.get("initial_stop_price"), t.get("target_price"))
        setup_keys.add(key)
    n_unique = len(setup_keys)

    # Event clustering by timestamp proximity
    timestamps = sorted([t.get("entry_timestamp") or t.get("setup_timestamp") or 0 for t in all_trades])
    clusters = []
    current_cluster = []

    for ts in timestamps:
        if not current_cluster:
            current_cluster.append(ts)
        else:
            if ts - current_cluster[-1] <= window_seconds:
                current_cluster.append(ts)
            else:
                clusters.append(current_cluster)
                current_cluster = [ts]
    if current_cluster:
        clusters.append(current_cluster)

    overlapping_trades = sum(len(c) - 1 for c in clusters if len(c) > 1)

    return {
        "raw_trade_count": n_raw,
        "unique_setup_count": n_unique,
        "overlapping_trade_count": overlapping_trades,
        "event_cluster_count": len(clusters),
        "cluster_details": [f"Cluster_{idx+1}: {len(c)} trades" for idx, c in enumerate(clusters) if len(c) > 1]
    }


def run_performance_forensics(h0_path: str, anchor2_path: str) -> Dict[str, Any]:
    """Master analytical runner."""
    print("=" * 80)
    print("EXECUTING INSTITUTIONAL PERFORMANCE FORENSICS ENGINE")
    print("=" * 80)

    # Load replay artifacts
    with open(h0_path, "r") as fp:
        h0_data = json.load(fp)
    with open(anchor2_path, "r") as fp:
        a2_data = json.load(fp)

    inventory = audit_historical_data_inventory()
    h0_waterfall = build_alpha_waterfall(h0_data["stream_results"], h0_data["all_trades"])
    a2_waterfall = build_alpha_waterfall(a2_data["stream_results"], a2_data["all_trades"])

    h0_mfe = analyze_mfe_realized_r(h0_data["all_trades"])
    a2_mfe = analyze_mfe_realized_r(a2_data["all_trades"])

    h0_mae = analyze_mae_forensics(h0_data["all_trades"])
    a2_mae = analyze_mae_forensics(a2_data["all_trades"])

    a2_timing = analyze_time_to_excursion(a2_data["all_trades"])
    a2_target_test = test_4r_target_reality(a2_data["all_trades"])

    h0_exit = analyze_exit_attribution(h0_data["all_trades"])
    a2_exit = analyze_exit_attribution(a2_data["all_trades"])

    a2_prov = analyze_target_provenance(a2_data["all_trades"])
    a2_assets = analyze_asset_attribution(a2_data["all_trades"])
    a2_timeframes = analyze_timeframe_attribution(a2_data["all_trades"])
    a2_regimes = analyze_regime_diagnostics(a2_data["all_trades"])
    a2_elasticity = analyze_cost_elasticity(a2_data["all_trades"])
    a2_dependency = analyze_trade_dependency(a2_data["all_trades"])

    report_payload = {
        "inventory": inventory,
        "manifest_h0": h0_data["manifest"],
        "manifest_a2": a2_data["manifest"],
        "aggregate_h0": h0_data["aggregate_performance"],
        "aggregate_a2": a2_data["aggregate_performance"],
        "h0_waterfall": h0_waterfall,
        "a2_waterfall": a2_waterfall,
        "h0_mfe": h0_mfe,
        "a2_mfe": a2_mfe,
        "h0_mae": h0_mae,
        "a2_mae": a2_mae,
        "time_to_excursion": a2_timing,
        "target_reality_test": a2_target_test,
        "exit_attribution_h0": h0_exit,
        "exit_attribution_a2": a2_exit,
        "target_provenance": a2_prov,
        "asset_attribution": a2_assets,
        "timeframe_attribution": a2_timeframes,
        "regime_diagnostics": a2_regimes,
        "cost_elasticity": a2_elasticity,
        "trade_dependency": a2_dependency
    }

    out_json = "/home/mrcn2/crypto-platform/scratch/performance_forensics_summary.json"
    with open(out_json, "w") as fp:
        json.dump(report_payload, fp, indent=2)

    print(f"✅ Forensics payload saved to: {out_json}")
    return report_payload


run_alpha_forensics = run_performance_forensics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Performance Forensics Engine")
    parser.add_argument("--h0", type=str, default="/home/mrcn2/crypto-platform/scratch/h0_dev_certified_results.json", help="H0 results path")
    parser.add_argument("--anchor2", type=str, default="/home/mrcn2/crypto-platform/scratch/anchor2_dev_certified_results.json", help="ANCHOR_2 results path")
    args = parser.parse_args()

    h0_file = args.h0
    a2_file = args.anchor2
    if not os.path.exists(h0_file):
        h0_file = "/home/mrcn2/crypto-platform/scratch/canonical_h0_dev_results.json"
    if not os.path.exists(a2_file):
        a2_file = "/home/mrcn2/crypto-platform/scratch/canonical_anchor_2_dev_results.json"

    if os.path.exists(h0_file) and os.path.exists(a2_file):
        run_performance_forensics(h0_file, a2_file)
    else:
        print(f"Required result files missing. Found h0: {os.path.exists(h0_file)}, a2: {os.path.exists(a2_file)}")
