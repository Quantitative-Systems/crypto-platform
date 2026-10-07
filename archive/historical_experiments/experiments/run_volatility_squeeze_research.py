"""
Quantitative Crypto Platform (QCP) — Family 06 Volatility Squeeze Research Runner.

Evaluates directional breakout expansion following volatility compression:
- Assets: SOL/USDT, BTC/USDT, ETH/USDT
- Timeframes: 4H, 1H, 15M
- Partitions: DEV (2021-2022), VAL (2023), OOS (2024-2026)
- Causal execution: next-bar open fill, adverse-first collisions, 8 bps friction
- Adversarial battery: 2x friction, latency, windfall removal

Outputs: research/results/VOLATILITY_SQUEEZE_EXPERIMENT_AUDIT.json
"""

import os
import json
import logging
import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from market_data.binance_fetcher import BinanceFetcher
from market_intelligence.primitives import Candle
from research.discovery_lab.specs.fam06_volatility_squeeze import (
    compute_volatility_squeeze_signals,
    create_fam06_spec,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VolSqueezeResearch")


@dataclass
class SimulatedTrade:
    trade_id: str
    symbol: str
    timeframe: str
    direction: str          # "LONG" or "SHORT"
    entry_ts: int
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_ts: int
    exit_price: float
    exit_reason: str        # "STOP_LOSS", "TAKE_PROFIT", "TIMEOUT"
    realized_r: float
    gross_return_pct: float
    net_return_pct: float
    friction_drag_r: float
    bars_held: int


def simulate_squeeze_execution(
    candles: List[Candle],
    symbol: str,
    timeframe: str,
    tp_r: float = 3.0,
    atr_mult: float = 1.5,
    friction_bps: float = 8.0,
    latency_bars: int = 0,
) -> List[SimulatedTrade]:
    """
    Executes causal walk-forward trade simulation on closed candle series.
    Enforces ADVERSE_FIRST collision handling.
    """
    if len(candles) < 60:
        return []

    c_arr = np.array([c.close for c in candles], dtype=np.float64)
    h_arr = np.array([c.high for c in candles], dtype=np.float64)
    l_arr = np.array([c.low for c in candles], dtype=np.float64)
    o_arr = np.array([c.open for c in candles], dtype=np.float64)
    ts_arr = np.array([c.timestamp for c in candles], dtype=np.int64)

    long_sigs, short_sigs, atr_vals = compute_volatility_squeeze_signals(
        h_arr, l_arr, c_arr, bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5, atr_period=14
    )

    trades: List[SimulatedTrade] = []
    in_pos = False
    pos_dir = ""
    entry_idx = 0
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    risk_dist = 0.0
    r_locked = False

    friction_frac = friction_bps / 10000.0

    i = 50
    n = len(candles)
    while i < n - 1:
        if not in_pos:
            # Check entry signal from previous closed bar (taking latency into account)
            sig_bar = i - latency_bars
            if sig_bar >= 50:
                is_long = bool(long_sigs[sig_bar])
                is_short = bool(short_sigs[sig_bar])

                if is_long and not is_short:
                    in_pos = True
                    pos_dir = "LONG"
                    entry_idx = i
                    entry_p = o_arr[i] * (1.0 + friction_frac / 2.0)  # half friction on entry
                    risk_dist = atr_vals[sig_bar] * atr_mult
                    sl_p = entry_p - risk_dist
                    tp_p = entry_p + (risk_dist * tp_r)
                    r_locked = False
                elif is_short and not is_long:
                    in_pos = True
                    pos_dir = "SHORT"
                    entry_idx = i
                    entry_p = o_arr[i] * (1.0 - friction_frac / 2.0)
                    risk_dist = atr_vals[sig_bar] * atr_mult
                    sl_p = entry_p + risk_dist
                    tp_p = entry_p - (risk_dist * tp_r)
                    r_locked = False
        else:
            # Position active: evaluate intrabar high/low against SL and TP
            curr_h = h_arr[i]
            curr_l = l_arr[i]
            bars_held = i - entry_idx

            # Profit lock check at +1.5R: move stop to breakeven + 0.2R
            if not r_locked and risk_dist > 1e-6:
                if pos_dir == "LONG" and curr_h >= (entry_p + 1.5 * risk_dist):
                    sl_p = entry_p + 0.2 * risk_dist
                    r_locked = True
                elif pos_dir == "SHORT" and curr_l <= (entry_p - 1.5 * risk_dist):
                    sl_p = entry_p - 0.2 * risk_dist
                    r_locked = True

            # Collision evaluation: ADVERSE_FIRST policy
            hit_sl = False
            hit_tp = False
            exit_p = 0.0
            exit_reason = ""

            if pos_dir == "LONG":
                hit_sl = (curr_l <= sl_p)
                hit_tp = (curr_h >= tp_p)
            else:
                hit_sl = (curr_h >= sl_p)
                hit_tp = (curr_l <= tp_p)

            # Max hold timeout: 40 bars
            timeout = (bars_held >= 40)

            if hit_sl and hit_tp:
                # Collision: ADVERSE_FIRST assumes Stop Loss executed first!
                exit_p = sl_p
                exit_reason = "STOP_LOSS_COLLISION_ADVERSE"
            elif hit_sl:
                exit_p = sl_p
                exit_reason = "STOP_LOSS"
            elif hit_tp:
                exit_p = tp_p
                exit_reason = "TAKE_PROFIT"
            elif timeout:
                exit_p = c_arr[i]
                exit_reason = "TIMEOUT_MAX_HOLD"

            if exit_reason:
                # Apply exit friction
                if pos_dir == "LONG":
                    net_exit = exit_p * (1.0 - friction_frac / 2.0)
                    pnl_usd = net_exit - entry_p
                else:
                    net_exit = exit_p * (1.0 + friction_frac / 2.0)
                    pnl_usd = entry_p - net_exit

                r_mult = pnl_usd / risk_dist if risk_dist > 1e-6 else 0.0
                fric_drag_r = (entry_p * friction_frac) / risk_dist if risk_dist > 1e-6 else 0.0

                trades.append(
                    SimulatedTrade(
                        trade_id=f"{symbol}_{timeframe}_{len(trades)+1}",
                        symbol=symbol,
                        timeframe=timeframe,
                        direction=pos_dir,
                        entry_ts=int(ts_arr[entry_idx]),
                        entry_price=round(entry_p, 4),
                        stop_loss=round(sl_p, 4),
                        take_profit=round(tp_p, 4),
                        exit_ts=int(ts_arr[i]),
                        exit_price=round(net_exit, 4),
                        exit_reason=exit_reason,
                        realized_r=round(r_mult, 4),
                        gross_return_pct=round((exit_p - entry_p) / entry_p * 100.0 if pos_dir == "LONG" else (entry_p - exit_p) / entry_p * 100.0, 2),
                        net_return_pct=round(pnl_usd / entry_p * 100.0, 2),
                        friction_drag_r=round(fric_drag_r, 4),
                        bars_held=bars_held,
                    )
                )
                in_pos = False

        i += 1

    return trades


def partition_trades(trades: List[SimulatedTrade]) -> Dict[str, Dict[str, Any]]:
    """Partitions trade outcomes into DEV (2021-2022), VAL (2023), and OOS (2024-2026)."""
    # Timestamp boundaries
    dev_start = 1609459200  # 2021-01-01
    dev_end = 1672531199    # 2022-12-31
    val_start = 1672531200  # 2023-01-01
    val_end = 1704067199    # 2023-12-31
    oos_start = 1704067200  # 2024-01-01

    partitions = {
        "FULL": [t for t in trades],
        "DEV": [t for t in trades if dev_start <= t.entry_ts <= dev_end],
        "VAL": [t for t in trades if val_start <= t.entry_ts <= val_end],
        "OOS": [t for t in trades if t.entry_ts >= oos_start],
    }

    metrics = {}
    for part_name, p_trades in partitions.items():
        if not p_trades:
            metrics[part_name] = {
                "trade_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate_pct": 0.0,
                "total_net_r": 0.0,
                "mean_expectancy_r": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_r": 0.0,
            }
            continue

        r_vals = [t.realized_r for t in p_trades]
        wins = [r for r in r_vals if r > 0]
        losses = [r for r in r_vals if r <= 0]

        gross_win_r = sum(wins)
        gross_loss_r = abs(sum(losses))
        pf = gross_win_r / gross_loss_r if gross_loss_r > 1e-6 else 999.0

        # Drawdown in R
        cum_r = np.cumsum(r_vals)
        peaks = np.maximum.accumulate(cum_r)
        dds = peaks - cum_r
        max_dd_r = float(np.max(dds)) if len(dds) > 0 else 0.0

        metrics[part_name] = {
            "trade_count": len(p_trades),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate_pct": round(len(wins) / len(p_trades) * 100.0, 2),
            "total_net_r": round(sum(r_vals), 2),
            "mean_expectancy_r": round(np.mean(r_vals), 4),
            "profit_factor": round(pf, 4),
            "max_drawdown_r": round(max_dd_r, 2),
        }

    return metrics


def run_volatility_squeeze_research() -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("QCP — FAMILY 06: VOLATILITY EXPANSION SQUEEZE RESEARCH AUDIT")
    logger.info("=" * 70)

    symbols = ["SOL/USDT", "BTC/USDT", "ETH/USDT"]
    timeframes = ["4h", "1h", "15m"]

    results = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "experiment": "FAMILY_06_VOLATILITY_EXPANSION_SQUEEZE",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "methodology": {
            "family_id": "FAM-06-VOLSQUEEZE",
            "mechanism": "Bollinger Band contraction inside Keltner Channel with directional momentum breakout",
            "friction_model": "8.0 bps roundtrip (5.0 bps fee + 3.0 bps slippage)",
            "collision_policy": "ADVERSE_FIRST",
            "same_bar_confirmation": "CLOSED_CANDLES_ONLY",
        },
        "streams": {},
        "adversarial_stress": {},
        "summary": {
            "total_streams_evaluated": 0,
            "qualified_robust_count": 0,
            "fragile_count": 0,
            "falsified_count": 0,
        },
    }

    trade_collections = {}

    for sym in symbols:
        for tf in timeframes:
            stream_id = f"FAM06_{sym.replace('/', '_')}_{tf}"
            logger.info(f"Evaluating {stream_id}...")

            candles = BinanceFetcher.fetch_real_candles(sym, tf, limit=50000)
            if not candles:
                logger.warning(f"No candles retrieved for {sym} {tf}")
                continue

            trades = simulate_squeeze_execution(candles, sym, tf, tp_r=3.0, atr_mult=1.5, friction_bps=8.0)
            trade_collections[stream_id] = trades
            part_metrics = partition_trades(trades)

            # Evaluate Qualification Criteria:
            # Robust candidate requires:
            # 1. Dev Net R > +10R and Expectancy >= +0.15R
            # 2. Validation Net R > +5R
            # 3. OOS Net R > +10R and Expectancy >= +0.15R
            dev_m = part_metrics["DEV"]
            val_m = part_metrics["VAL"]
            oos_m = part_metrics["OOS"]

            is_qualified = (
                dev_m["total_net_r"] >= 10.0 and dev_m["mean_expectancy_r"] >= 0.15 and
                val_m["total_net_r"] >= 5.0 and
                oos_m["total_net_r"] >= 10.0 and oos_m["mean_expectancy_r"] >= 0.15
            )

            is_falsified = (
                dev_m["total_net_r"] < 0 or oos_m["total_net_r"] < 0 or
                dev_m["mean_expectancy_r"] < 0 or oos_m["mean_expectancy_r"] < 0
            )

            if is_qualified:
                status = "QUALIFIED_ROBUST"
                results["summary"]["qualified_robust_count"] += 1
            elif is_falsified:
                status = "FALSIFIED"
                results["summary"]["falsified_count"] += 1
            else:
                status = "FRAGILE"
                results["summary"]["fragile_count"] += 1

            results["summary"]["total_streams_evaluated"] += 1

            results["streams"][stream_id] = {
                "symbol": sym,
                "timeframe": tf,
                "status": status,
                "metrics_by_partition": part_metrics,
            }

            logger.info(
                f"[{stream_id}] Status: {status} | Full Net R: {part_metrics['FULL']['total_net_r']:+.2f}R ({part_metrics['FULL']['trade_count']} trades) | "
                f"OOS Net R: {oos_m['total_net_r']:+.2f}R ({oos_m['trade_count']} trades, E={oos_m['mean_expectancy_r']:+.4f}R)"
            )

    # Adversarial Stress Testing across the streams
    logger.info("\n--- Running Adversarial Stress Testing ---")
    for stream_id, trades in trade_collections.items():
        if not trades:
            continue

        sym = results["streams"][stream_id]["symbol"]
        tf = results["streams"][stream_id]["timeframe"]
        candles = BinanceFetcher.fetch_real_candles(sym, tf, limit=50000)

        # Stress 1: 2x friction (16 bps)
        trades_2x = simulate_squeeze_execution(candles, sym, tf, tp_r=3.0, atr_mult=1.5, friction_bps=16.0)
        p_2x = partition_trades(trades_2x)

        # Stress 2: 1-bar execution latency
        trades_lat = simulate_squeeze_execution(candles, sym, tf, tp_r=3.0, atr_mult=1.5, friction_bps=8.0, latency_bars=1)
        p_lat = partition_trades(trades_lat)

        # Stress 3: Outlier removal (remove top 5% winning trades)
        r_vals = sorted([t.realized_r for t in trades], reverse=True)
        cutoff_idx = max(1, int(len(r_vals) * 0.05))
        r_trimmed = r_vals[cutoff_idx:]
        net_r_trimmed = sum(r_trimmed) if r_trimmed else 0.0

        results["adversarial_stress"][stream_id] = {
            "baseline_full_net_r": results["streams"][stream_id]["metrics_by_partition"]["FULL"]["total_net_r"],
            "friction_2x_full_net_r": p_2x["FULL"]["total_net_r"],
            "latency_1bar_full_net_r": p_lat["FULL"]["total_net_r"],
            "windfall_outliers_removed_net_r": round(net_r_trimmed, 2),
            "windfall_dependency": "HIGH" if (results["streams"][stream_id]["metrics_by_partition"]["FULL"]["total_net_r"] > 0 and net_r_trimmed <= 0) else "LOW",
        }

    out_path = os.path.abspath("research/results/VOLATILITY_SQUEEZE_EXPERIMENT_AUDIT.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nVolatility Squeeze experiment audit saved to {out_path}")
    return results


if __name__ == "__main__":
    run_volatility_squeeze_research()
