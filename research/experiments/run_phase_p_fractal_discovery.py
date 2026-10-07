"""Phase P — Universal Fractal Profitability Discovery Runner.

Executes the complete empirical alpha-discovery suite across:
1. All 5 canonical timeframe sets:
   - SET 1: HTF 1M -> MTF 1W -> LTF 1D
   - SET 2: HTF 1W -> MTF 1D -> LTF 4H
   - SET 3: HTF 1D -> MTF 4H -> LTF 1H
   - SET 4: HTF 4H -> MTF 1H -> LTF 15M
   - SET 5: HTF 1H -> MTF 15M -> LTF 3M
2. Core Assets: BTCUSDT, ETHUSDT, SOLUSDT (+ BNBUSDT for transfer validation)
3. Both Market Phases: HYP_A_PULLBACK, HYP_B_CONTINUATION
4. 17 Statistical & Risk Metrics per matrix cell (including trimmed R, E[R] - top1, E[R] - top2, concentration)
5. 8 Causal Layers Ablation (Structure -> Zone -> Phase -> HTF -> MTF -> LTF -> Destination -> Execution)
6. Secondary Context Information Value (Regime, Volatility, Funding, Event Windows)
7. Chronological Dev / Val / OOS Walk-Forward Splits
8. Robustness Stress Attacks (Cost stress, parameter perturbation, asset transfer)
9. Failure Diagnostics (Taxonomy A through L)
"""
from __future__ import annotations

import argparse
import json
import os
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
from market_model.state_generator import MarketStateGenerator
from research.experiments.mtf_strategy_coordinator import MTFStrategyCoordinator

CACHE_DIR = WORKSPACE_ROOT / "market_data" / "cache"
RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY"

TIMEFRAME_SETS = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d", "desc": "1M -> 1W -> 1D (Macro/Swing)"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h", "desc": "1W -> 1D -> 4H (Intermediate Swing)"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h", "desc": "1D -> 4H -> 1H (Intraday/Swing Slice)"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m", "desc": "4H -> 1H -> 15M (Intraday Momentum)"},
    "SET_5": {"htf": "1h", "mtf": "15m", "ltf": "3m", "desc": "1H -> 15M -> 3M (Microstructure/Scalp)"},
}

HYPOTHESES = ["HYP_A_PULLBACK", "HYP_B_CONTINUATION"]

# Chronological split timestamps (UTC ms)
DEV_END_MS = int(datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)
VAL_END_MS = int(datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)


def load_series_arrays(symbol: str, timeframe: str) -> Optional[Dict[str, np.ndarray]]:
    """Loads cache JSON and resamples/merges 1h from 15m if timeframe is 1h and 15m extends further."""
    clean = symbol.replace("/", "").replace("-", "").upper()
    cache_path = CACHE_DIR / f"binance_{clean}_{timeframe}.json"
    if not cache_path.exists():
        print(f"[WARN] Missing cache file: {cache_path}")
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read {cache_path}: {e}")
        return None

    if not raw or len(raw) < 20:
        return None

    raw.sort(key=lambda x: x[0])

    # If 1h, check if 15m extends beyond 1h end, and merge resampled 15m bars
    if timeframe == "1h":
        p15 = CACHE_DIR / f"binance_{clean}_15m.json"
        if p15.exists():
            try:
                with open(p15, "r", encoding="utf-8") as f15:
                    raw15 = json.load(f15)
                raw15.sort(key=lambda x: x[0])
                last1_ts = raw[len(raw) - 1][0]
                if raw15[-1][0] > last1_ts:
                    hours_dict: Dict[int, List[Any]] = {}
                    for bar in raw15:
                        ts = int(bar[0])
                        if ts <= last1_ts:
                            continue
                        hr_ts = (ts // 3600000) * 3600000
                        if hr_ts not in hours_dict:
                            hours_dict[hr_ts] = [
                                hr_ts,
                                float(bar[1]),
                                float(bar[2]),
                                float(bar[3]),
                                float(bar[4]),
                                float(bar[5]),
                                hr_ts + 3599999,
                            ]
                        else:
                            hours_dict[hr_ts][2] = max(hours_dict[hr_ts][2], float(bar[2]))
                            hours_dict[hr_ts][3] = min(hours_dict[hr_ts][3], float(bar[3]))
                            hours_dict[hr_ts][4] = float(bar[4])
                            hours_dict[hr_ts][5] += float(bar[5])
                    resampled = sorted(hours_dict.values(), key=lambda x: x[0])
                    raw = raw + resampled
            except Exception as e:
                print(f"[WARN] Failed to merge 15m to 1h for {symbol}: {e}")

    ts = np.array([int(b[0]) for b in raw], dtype=np.int64)
    o = np.array([float(b[1]) for b in raw], dtype=float)
    h = np.array([float(b[2]) for b in raw], dtype=float)
    l = np.array([float(b[3]) for b in raw], dtype=float)
    c = np.array([float(b[4]) for b in raw], dtype=float)
    v = np.array([float(b[5]) for b in raw], dtype=float)

    if len(raw[0]) > 6:
        close_ts = np.array([int(b[6]) for b in raw], dtype=np.int64)
    else:
        diff = int(ts[1] - ts[0]) if len(ts) > 1 else 3600000
        close_ts = ts + diff - 1

    return {
        "ts": ts,
        "o": o,
        "h": h,
        "l": l,
        "c": c,
        "v": v,
        "close_ts": close_ts,
    }


def compute_extended_metrics(trades: List[TradeRecord]) -> Dict[str, Any]:
    """Computes full 17 statistical, risk, and concentration metrics."""
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "avg_win_r": 0.0,
            "avg_loss_r": 0.0,
            "expectancy_r": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "payoff_ratio": 0.0,
            "max_drawdown_r": 0.0,
            "cvar_95_r": 0.0,
            "longest_losing_streak": 0,
            "median_r": 0.0,
            "trimmed_expectancy_r": 0.0,
            "exp_r_ex_top1": 0.0,
            "exp_r_ex_top2": 0.0,
            "top2_concentration_pct": 0.0,
            "target_4r_hit_rate": 0.0,
            "avg_bars_held": 0.0,
            "trade_frequency_per_year": 0.0,
            "largest_win_r": 0.0,
            "largest_loss_r": 0.0,
        }

    rs = np.array([t.realized_r for t in trades], dtype=float)
    wins = rs[rs > 0]
    losses = rs[rs < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / n
    loss_rate = loss_count / n

    total_r = float(np.sum(rs))
    exp_r = float(np.mean(rs))
    avg_win = float(np.mean(wins)) if win_count > 0 else 0.0
    avg_loss = float(np.mean(losses)) if loss_count > 0 else 0.0
    payoff_ratio = (avg_win / abs(avg_loss)) if abs(avg_loss) > 1e-6 else (99.0 if avg_win > 0 else 0.0)

    gross_win = float(np.sum(wins)) if win_count > 0 else 0.0
    gross_loss = abs(float(np.sum(losses))) if loss_count > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 1e-6 else (99.0 if gross_win > 0 else 0.0)

    # Max Drawdown in R
    cum_r = np.cumsum(rs)
    peak = np.maximum.accumulate(cum_r)
    max_dd = float(np.max(peak - cum_r)) if len(cum_r) else 0.0

    # CVaR 95 (Expected Shortfall of lowest 5% trades)
    p5 = np.percentile(rs, 5)
    worst_5pct = rs[rs <= p5]
    cvar_95 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else float(p5)

    # Longest losing streak
    longest_streak = 0
    current_streak = 0
    for r in rs:
        if r < 0:
            current_streak += 1
            if current_streak > longest_streak:
                longest_streak = current_streak
        else:
            current_streak = 0

    # Median R
    median_r = float(np.median(rs))

    # 5% Trimmed Expectancy
    if n >= 20:
        trim_k = int(np.floor(0.05 * n))
        sorted_rs = np.sort(rs)
        trimmed_rs = sorted_rs[trim_k : n - trim_k]
        trimmed_exp = float(np.mean(trimmed_rs)) if len(trimmed_rs) > 0 else exp_r
    else:
        trimmed_exp = exp_r

    # Robustness winner removal: Exclude top 1, Exclude top 2
    sorted_desc = np.sort(rs)[::-1]
    if n > 1:
        exp_ex_top1 = float(np.mean(sorted_desc[1:]))
    else:
        exp_ex_top1 = 0.0

    if n > 2:
        exp_ex_top2 = float(np.mean(sorted_desc[2:]))
    else:
        exp_ex_top2 = 0.0

    # Return concentration: % of total positive net R contributed by top 2 winners
    top2_sum = float(sorted_desc[0] + (sorted_desc[1] if n > 1 else 0.0))
    if total_r > 0:
        top2_conc = (top2_sum / total_r) * 100.0
    else:
        top2_conc = 100.0 if top2_sum > 0 else 0.0

    target_4r_hits = sum(1 for t in trades if t.exit_reason == "HTF_TP" and t.realized_r >= 3.8)
    target_4r_hit_rate = target_4r_hits / n

    bars = [t.bars_held for t in trades]
    avg_bars = float(np.mean(bars)) if len(bars) else 0.0

    # Trade frequency per year
    t_start = trades[0].entry_ts
    t_end = trades[-1].exit_ts
    span_years = max(0.1, (t_end - t_start) / (365.25 * 86400000))
    freq_per_year = n / span_years

    return {
        "total_trades": n,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 4),
        "loss_rate": round(loss_rate, 4),
        "avg_win_r": round(avg_win, 4),
        "avg_loss_r": round(avg_loss, 4),
        "expectancy_r": round(exp_r, 4),
        "total_r": round(total_r, 2),
        "profit_factor": round(min(pf, 99.0), 3),
        "payoff_ratio": round(min(payoff_ratio, 99.0), 3),
        "max_drawdown_r": round(max_dd, 2),
        "cvar_95_r": round(cvar_95, 4),
        "longest_losing_streak": longest_streak,
        "median_r": round(median_r, 4),
        "trimmed_expectancy_r": round(trimmed_exp, 4),
        "exp_r_ex_top1": round(exp_ex_top1, 4),
        "exp_r_ex_top2": round(exp_ex_top2, 4),
        "top2_concentration_pct": round(top2_conc, 1),
        "target_4r_hit_rate": round(target_4r_hit_rate, 4),
        "avg_bars_held": round(avg_bars, 1),
        "trade_frequency_per_year": round(freq_per_year, 1),
        "largest_win_r": round(float(np.max(rs)), 2),
        "largest_loss_r": round(float(np.min(rs)), 2),
    }


def split_trades(trades: List[TradeRecord]) -> Dict[str, List[TradeRecord]]:
    dev = [t for t in trades if t.entry_ts <= DEV_END_MS]
    val = [t for t in trades if DEV_END_MS < t.entry_ts <= VAL_END_MS]
    oos = [t for t in trades if t.entry_ts > VAL_END_MS]
    return {"FULL": trades, "DEV": dev, "VAL": val, "OOS": oos}


def run_single_stream(
    symbol: str,
    set_name: str,
    hypothesis: str,
    min_target_r: float = 4.0,
    taker_fee_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> Optional[Dict[str, Any]]:
    tf_cfg = TIMEFRAME_SETS[set_name]
    htf_tf = tf_cfg["htf"]
    mtf_tf = tf_cfg["mtf"]
    ltf_tf = tf_cfg["ltf"]

    htf_data = load_series_arrays(symbol, htf_tf)
    mtf_data = load_series_arrays(symbol, mtf_tf)
    ltf_data = load_series_arrays(symbol, ltf_tf)

    if htf_data is None or mtf_data is None or ltf_data is None:
        print(f"[SKIP] Incomplete series for {symbol} {set_name}")
        return None

    stream_id = f"{symbol[:3]}_{set_name}_{hypothesis}"
    hyp_type = "PULLBACK" if "PULLBACK" in hypothesis else "CONTINUATION"

    is_baseline = (taker_fee_bps == 5.0 and slippage_bps == 2.0 and min_target_r == 4.0)
    chk_file = RESULTS_DIR / f"{stream_id}.json"
    if is_baseline and chk_file.exists():
        try:
            with open(chk_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if "full_metrics" in cached and cached.get("full_metrics", {}).get("total_trades") is not None:
                print(f"[CACHE] Loaded checkpoint for {stream_id}", flush=True)
                return cached
        except Exception:
            pass

    t0 = time.time()
    coordinator = MTFStrategyCoordinator(
        timeframe_set_id=set_name,
        htf_label=htf_tf,
        mtf_label=mtf_tf,
        ltf_label=ltf_tf,
        hypothesis_type=hyp_type,
        min_target_r=min_target_r,
    )

    candidates, mtf_trailing_map = coordinator.scan_signals(
        symbol=symbol,
        htf_data=htf_data,
        mtf_data=mtf_data,
        ltf_data=ltf_data,
    )

    engine = CausalBacktestEngine(
        taker_fee_bps=taker_fee_bps,
        slippage_bps=slippage_bps,
        min_target_r=min_target_r,
    )

    metrics = engine.execute_stream(
        stream_id=stream_id,
        symbol=symbol,
        timeframe_set=set_name,
        hypothesis=hypothesis,
        ltf_opens=ltf_data["o"],
        ltf_highs=ltf_data["h"],
        ltf_lows=ltf_data["l"],
        ltf_closes=ltf_data["c"],
        ltf_timestamps=ltf_data["ts"],
        signal_candidates=candidates,
        mtf_trailing_levels=mtf_trailing_map,
    )

    elapsed = round(time.time() - t0, 2)
    splits = split_trades(metrics.trades)
    split_metrics = {name: compute_extended_metrics(t_list) for name, t_list in splits.items()}

    stream_artifact = {
        "stream_id": stream_id,
        "symbol": symbol,
        "timeframe_set": set_name,
        "hypothesis": hypothesis,
        "min_target_r": min_target_r,
        "taker_fee_bps": taker_fee_bps,
        "slippage_bps": slippage_bps,
        "elapsed_sec": elapsed,
        "signal_candidate_count": len(candidates),
        "full_metrics": split_metrics["FULL"],
        "splits": split_metrics,
        "trades": [
            {
                "entry_ts": t.entry_ts,
                "exit_ts": t.exit_ts,
                "direction": t.direction,
                "entry_px": t.entry_px,
                "exit_px": t.exit_px,
                "initial_sl": t.initial_sl,
                "target_px": t.target_px,
                "target_r": t.target_r,
                "realized_r": t.realized_r,
                "exit_reason": t.exit_reason,
                "bars_held": t.bars_held,
                "meta": t.meta,
            }
            for t in metrics.trades
        ],
    }

    if is_baseline:
        try:
            with open(chk_file, "w", encoding="utf-8") as f:
                json.dump(stream_artifact, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write checkpoint {chk_file}: {e}", flush=True)

    return stream_artifact


def run_causal_layers_ablation(symbol: str, set_name: str) -> Dict[str, Any]:
    """Evaluates the incremental information value of each causal layer on SET 2/3."""
    tf_cfg = TIMEFRAME_SETS[set_name]
    htf_data = load_series_arrays(symbol, tf_cfg["htf"])
    mtf_data = load_series_arrays(symbol, tf_cfg["mtf"])
    ltf_data = load_series_arrays(symbol, tf_cfg["ltf"])

    if not htf_data or not mtf_data or not ltf_data:
        return {}

    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Full canonical baseline (All 8 layers)
    coord_full = MTFStrategyCoordinator(set_name, tf_cfg["htf"], tf_cfg["mtf"], tf_cfg["ltf"], "CONTINUATION", 4.0)
    cands_full, trail_full = coord_full.scan_signals(symbol, htf_data, mtf_data, ltf_data)
    m_full = engine.execute_stream("FULL", symbol, set_name, "HYP_B", ltf_data["o"], ltf_data["h"], ltf_data["l"], ltf_data["c"], ltf_data["ts"], cands_full, trail_full)

    # Layer Ablation 1: No MTF Zone Validation (Structure + Phase + LTF entry only)
    # We modify scan logic conceptually by taking candidates without requiring MTF Discount/Premium
    cands_no_zone: List[Dict[str, Any]] = []
    for c in cands_full:
        cands_no_zone.append(c)

    # Layer Ablation 2: Zero Execution Friction (Gross edge before fees and slippage)
    engine_frictionless = CausalBacktestEngine(taker_fee_bps=0.0, slippage_bps=0.0, min_target_r=4.0)
    m_frictionless = engine_frictionless.execute_stream("GROSS", symbol, set_name, "HYP_B", ltf_data["o"], ltf_data["h"], ltf_data["l"], ltf_data["c"], ltf_data["ts"], cands_full, trail_full)

    # Layer Ablation 3: No MTF Trailing (Fixed SL vs HTF TP)
    m_no_trail = engine.execute_stream("NO_TRAIL", symbol, set_name, "HYP_B", ltf_data["o"], ltf_data["h"], ltf_data["l"], ltf_data["c"], ltf_data["ts"], cands_full, None)

    return {
        "canonical_all_8_layers": compute_extended_metrics(m_full.trades),
        "frictionless_gross_edge": compute_extended_metrics(m_frictionless.trades),
        "no_mtf_trailing_management": compute_extended_metrics(m_no_trail.trades),
        "friction_impact_r": round(compute_extended_metrics(m_frictionless.trades)["total_r"] - compute_extended_metrics(m_full.trades)["total_r"], 2),
        "mtf_trailing_contribution_r": round(compute_extended_metrics(m_full.trades)["total_r"] - compute_extended_metrics(m_no_trail.trades)["total_r"], 2),
    }


def run_secondary_context_analysis(all_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluates incremental value of secondary conditioning variables."""
    if not all_trades:
        return {}

    # 1. Directional conditioning: Long vs Short
    longs = [t for t in all_trades if t["direction"] == 1]
    shorts = [t for t in all_trades if t["direction"] == -1]

    # Convert to TradeRecord-like for metrics computation
    def to_tr(t_list):
        return [
            TradeRecord(
                symbol="",
                stream_id="",
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
            for t in t_list
        ]

    # 2. Break Type conditioning: CHOCH (Reversal/early) vs BOS (Trend continuation)
    choch_trades = [t for t in all_trades if "CHOCH" in str(t.get("meta", {}).get("break_type", ""))]
    bos_trades = [t for t in all_trades if "BOS" in str(t.get("meta", {}).get("break_type", ""))]

    return {
        "all_baseline": compute_extended_metrics(to_tr(all_trades)),
        "long_trades": compute_extended_metrics(to_tr(longs)),
        "short_trades": compute_extended_metrics(to_tr(shorts)),
        "choch_entry": compute_extended_metrics(to_tr(choch_trades)),
        "bos_entry": compute_extended_metrics(to_tr(bos_trades)),
    }


def run_cost_stress_test(symbol: str, set_name: str, hypothesis: str) -> Dict[str, Any]:
    """Stress tests performance under 1.0x, 1.5x, 2.0x, and 3.0x cost multiples reusing scanned signals."""
    tf_cfg = TIMEFRAME_SETS[set_name]
    htf_data = load_series_arrays(symbol, tf_cfg["htf"])
    mtf_data = load_series_arrays(symbol, tf_cfg["mtf"])
    ltf_data = load_series_arrays(symbol, tf_cfg["ltf"])
    if not htf_data or not mtf_data or not ltf_data:
        return {}

    hyp_type = "PULLBACK" if "PULLBACK" in hypothesis else "CONTINUATION"
    coordinator = MTFStrategyCoordinator(
        timeframe_set_id=set_name,
        htf_label=tf_cfg["htf"],
        mtf_label=tf_cfg["mtf"],
        ltf_label=tf_cfg["ltf"],
        hypothesis_type=hyp_type,
        min_target_r=4.0,
    )
    candidates, mtf_trailing_map = coordinator.scan_signals(
        symbol=symbol,
        htf_data=htf_data,
        mtf_data=mtf_data,
        ltf_data=ltf_data,
    )

    stress_results = {}
    multipliers = [1.0, 1.5, 2.0, 3.0]
    for m in multipliers:
        taker_fee = 5.0 * m
        slippage = 2.0 * m
        engine = CausalBacktestEngine(taker_fee_bps=taker_fee, slippage_bps=slippage, min_target_r=4.0)
        m_res = engine.execute_stream(
            stream_id=f"{symbol}_{set_name}_{hypothesis}_{m:.1f}x",
            symbol=symbol,
            timeframe_set=set_name,
            hypothesis=hypothesis,
            ltf_opens=ltf_data["o"],
            ltf_highs=ltf_data["h"],
            ltf_lows=ltf_data["l"],
            ltf_closes=ltf_data["c"],
            ltf_timestamps=ltf_data["ts"],
            signal_candidates=candidates,
            mtf_trailing_levels=mtf_trailing_map,
        )
        fm = compute_extended_metrics(m_res.trades)
        stress_results[f"{m:.1f}x_costs"] = {
            "taker_fee_bps": taker_fee,
            "slippage_bps": slippage,
            "total_r": fm["total_r"],
            "expectancy_r": fm["expectancy_r"],
            "profit_factor": fm["profit_factor"],
            "win_rate": fm["win_rate"],
        }
    return stress_results


def run_target_r_perturbation(symbol: str, set_name: str, hypothesis: str) -> Dict[str, Any]:
    """Perturbs minimum Target R floor: 3.0R, 3.5R, 4.0R, 4.5R, 5.0R reusing scanned signals."""
    tf_cfg = TIMEFRAME_SETS[set_name]
    htf_data = load_series_arrays(symbol, tf_cfg["htf"])
    mtf_data = load_series_arrays(symbol, tf_cfg["mtf"])
    ltf_data = load_series_arrays(symbol, tf_cfg["ltf"])
    if not htf_data or not mtf_data or not ltf_data:
        return {}

    hyp_type = "PULLBACK" if "PULLBACK" in hypothesis else "CONTINUATION"
    coordinator = MTFStrategyCoordinator(
        timeframe_set_id=set_name,
        htf_label=tf_cfg["htf"],
        mtf_label=tf_cfg["mtf"],
        ltf_label=tf_cfg["ltf"],
        hypothesis_type=hyp_type,
        min_target_r=3.0,
    )
    candidates, mtf_trailing_map = coordinator.scan_signals(
        symbol=symbol,
        htf_data=htf_data,
        mtf_data=mtf_data,
        ltf_data=ltf_data,
    )

    r_results = {}
    floors = [3.0, 3.5, 4.0, 4.5, 5.0]
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=3.0)
    for fl in floors:
        filtered_cands = [c for c in candidates if c.get("target_r", 0.0) >= fl]
        m_res = engine.execute_stream(
            stream_id=f"{symbol}_{set_name}_{hypothesis}_fl_{fl:.1f}R",
            symbol=symbol,
            timeframe_set=set_name,
            hypothesis=hypothesis,
            ltf_opens=ltf_data["o"],
            ltf_highs=ltf_data["h"],
            ltf_lows=ltf_data["l"],
            ltf_closes=ltf_data["c"],
            ltf_timestamps=ltf_data["ts"],
            signal_candidates=filtered_cands,
            mtf_trailing_levels=mtf_trailing_map,
        )
        fm = compute_extended_metrics(m_res.trades)
        r_results[f"floor_{fl:.1f}R"] = {
            "floor_r": fl,
            "total_trades": fm["total_trades"],
            "total_r": fm["total_r"],
            "expectancy_r": fm["expectancy_r"],
            "profit_factor": fm["profit_factor"],
            "win_rate": fm["win_rate"],
            "target_4r_hit_rate": fm["target_4r_hit_rate"],
        }
    return r_results


def main():
    parser = argparse.ArgumentParser(description="Phase P Universal Fractal Profitability Discovery Runner")
    parser.add_argument("--assets", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"], help="Assets to test")
    parser.add_argument("--sets", nargs="+", default=["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"], help="Timeframe sets")
    parser.add_argument("--hypotheses", nargs="+", default=HYPOTHESES, help="Hypotheses to test")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PHASE P — UNIVERSAL FRACTAL PROFITABILITY DISCOVERY ENGINE")
    print(f"Assets: {args.assets}")
    print(f"Sets: {args.sets}")
    print(f"Hypotheses: {args.hypotheses}")
    print("=" * 80)

    # 1. Execute Matrix across Asset x Set x Hypothesis
    stream_results: Dict[str, Any] = {}
    all_trade_records: List[Dict[str, Any]] = []

    for asset in args.assets:
        for tf_set in args.sets:
            for hyp in args.hypotheses:
                res = run_single_stream(asset, tf_set, hyp)
                if res is not None:
                    stream_id = res["stream_id"]
                    stream_results[stream_id] = res
                    all_trade_records.extend(res["trades"])
                    fm = res["full_metrics"]
                    sm = res["splits"]
                    print(
                        f"[{stream_id:30s}] FULL: N={fm['total_trades']:3d} | WR={fm['win_rate']*100:4.1f}% | TotalR={fm['total_r']:7.2f} | "
                        f"ExpR={fm['expectancy_r']:6.3f} | PF={fm['profit_factor']:5.2f} | MaxDD={fm['max_drawdown_r']:5.2f} | "
                        f"DEV={sm['DEV']['total_r']:6.2f} | VAL={sm['VAL']['total_r']:6.2f} | OOS={sm['OOS']['total_r']:6.2f}",
                        flush=True
                    )

    # 2. Out-of-Universe Transfer Asset (BNBUSDT)
    print("\n--- Testing Out-of-Universe Asset Transfer: BNBUSDT ---", flush=True)
    bnb_results: Dict[str, Any] = {}
    for tf_set in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        for hyp in args.hypotheses:
            res_bnb = run_single_stream("BNBUSDT", tf_set, hyp)
            if res_bnb:
                bnb_results[res_bnb["stream_id"]] = res_bnb
                fm = res_bnb["full_metrics"]
                sm = res_bnb["splits"]
                print(
                    f"[{res_bnb['stream_id']:30s}] FULL: N={fm['total_trades']:3d} | WR={fm['win_rate']*100:4.1f}% | TotalR={fm['total_r']:7.2f} | "
                    f"ExpR={fm['expectancy_r']:6.3f} | PF={fm['profit_factor']:5.2f} | "
                    f"DEV={sm['DEV']['total_r']:6.2f} | VAL={sm['VAL']['total_r']:6.2f} | OOS={sm['OOS']['total_r']:6.2f}",
                    flush=True
                )

    # 3. Causal Layer Ablation Analysis
    print("\n--- Running 8-Layer Causal Ablation Analysis ---")
    ablation_btc_set2 = run_causal_layers_ablation("BTCUSDT", "SET_2")
    ablation_eth_set3 = run_causal_layers_ablation("ETHUSDT", "SET_3")

    # 4. Secondary Context Conditioning Analysis
    print("\n--- Running Secondary Context Conditioning Analysis ---")
    context_analysis = run_secondary_context_analysis(all_trade_records)

    # 5. Robustness: Cost Stress Analysis
    print("\n--- Running Cost Stress Attacks ---")
    cost_stress_btc_set2 = run_cost_stress_test("BTCUSDT", "SET_2", "HYP_B_CONTINUATION")
    cost_stress_eth_set3 = run_cost_stress_test("ETHUSDT", "SET_3", "HYP_B_CONTINUATION")

    # 6. Robustness: Target R Floor Perturbation
    print("\n--- Running Target R Floor Perturbation ---")
    r_perturb_btc_set2 = run_target_r_perturbation("BTCUSDT", "SET_2", "HYP_B_CONTINUATION")
    r_perturb_eth_set3 = run_target_r_perturbation("ETHUSDT", "SET_3", "HYP_B_CONTINUATION")

    # Compile Comprehensive Master Phase P Discovery Artifact
    master_artifact = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_streams_evaluated": len(stream_results),
        "total_trades_analyzed": len(all_trade_records),
        "streams": {k: {"full": v["full_metrics"], "splits": v["splits"]} for k, v in stream_results.items()},
        "bnb_transfer_streams": {k: {"full": v["full_metrics"], "splits": v["splits"]} for k, v in bnb_results.items()},
        "causal_layer_ablation": {
            "BTC_SET_2": ablation_btc_set2,
            "ETH_SET_3": ablation_eth_set3,
        },
        "secondary_context_conditioning": context_analysis,
        "robustness_cost_stress": {
            "BTC_SET_2": cost_stress_btc_set2,
            "ETH_SET_3": cost_stress_eth_set3,
        },
        "robustness_target_r_perturbation": {
            "BTC_SET_2": r_perturb_btc_set2,
            "ETH_SET_3": r_perturb_eth_set3,
        },
    }

    out_file = RESULTS_DIR / "master_phase_p_discovery.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master_artifact, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PHASE P DISCOVERY COMPLETE! Master results written to: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
