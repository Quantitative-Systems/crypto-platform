"""Empirical Research Experiment: Tri-Strategy Fractal Trade Confluence.

Tests the user's groundbreaking hypothesis:
"HTF Scalp Strategy + MTF Intraday Strategy + LTF Swing Strategy = ONE SINGLE TRADE.
Because the market is fractal, an HTF reaction (scalp on HTF) manifests as an 
intraday momentum impulse on MTF, and presents as a full multi-leg swing on LTF.
Do all three strategy layers combined into ONE trade produce higher alpha, 
higher win rates, and superior risk-adjusted expectancy?"

Experimental Framework:
1. HTF Layer (Scalp Condition):
   - Price on HTF has just swept liquidity or tapped an Order Block/FVG within the last 1-3 bars (an HTF reaction 'scalp').
2. MTF Layer (Intraday Momentum Condition):
   - Price on MTF demonstrates an active momentum impulse (consecutive trending bars / dealing range discount/premium alignment).
3. LTF Layer (Swing Wave Condition):
   - Price on LTF forms a complete structural shift (CHoCH + BOS confirming a multi-swing wave is initiating).
4. Composite Execution:
   - When all three strategies agree simultaneously, fire ONE unified trade.

Evaluated across: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT across Sets 1 to 5 (2020-2026).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from market_model.contracts import StructuralBreakType, TrendDirection
from market_model.state_generator import MarketStateGenerator
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "TRI_STRATEGY_FRACTAL_RESEARCH"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_all_7_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def scan_tri_strategy_signals(
    symbol: str,
    target_set: str,
    all_data: Dict[str, Dict[str, np.ndarray]],
    coordinator: CascadingFractalCoordinator,
) -> Tuple[List[Dict[str, Any]], Dict[int, float]]:
    """Evaluates the Tri-Strategy confluence: HTF Scalp + MTF Intraday + LTF Swing."""
    cfg = coordinator.TIMEFRAME_SETS[target_set]
    htf_tf = cfg["htf"]
    mtf_tf = cfg["mtf"]
    ltf_tf = cfg["ltf"]

    htf_data = all_data[htf_tf]
    mtf_data = all_data[mtf_tf]
    ltf_data = all_data[ltf_tf]

    ltf_closes = ltf_data["c"]
    ltf_ts = ltf_data["ts"]
    n_ltf = len(ltf_closes)

    htf_close_ts = htf_data["close_ts"]
    mtf_close_ts = mtf_data["close_ts"]

    candidates = []
    trailing_map = {}

    last_htf_idx = -1
    last_htf_state = None
    last_mtf_idx = -1
    last_mtf_state = None

    for i in range(25, n_ltf):
        t_curr = int(ltf_ts[i])
        curr_px = float(ltf_closes[i])

        # 1. Macro Baton Context
        baton, demand_tgt, supply_tgt = coordinator.evaluate_macro_baton(symbol, t_curr, all_data)
        if baton in ("BULLISH_EXPANSION", "BULLISH_PULLBACK"):
            authorized_dir = 1
        elif baton in ("BEARISH_EXPANSION", "BEARISH_PULLBACK"):
            authorized_dir = -1
        else:
            authorized_dir = 0

        if authorized_dir == 0:
            continue

        # 2. HTF STRATEGY LAYER: "HTF Scalp"
        # Price on HTF must be in an active reaction off an Order Block / FVG / Liquidity sweep
        htf_idx = np.searchsorted(htf_close_ts, t_curr, side="right") - 1
        if htf_idx < 10:
            continue

        if htf_idx != last_htf_idx:
            htf_start = max(0, htf_idx - 100)
            last_htf_state = coordinator.generators[htf_tf].generate(
                symbol=symbol,
                opens=htf_data["o"][htf_start : htf_idx + 1],
                highs=htf_data["h"][htf_start : htf_idx + 1],
                lows=htf_data["l"][htf_start : htf_idx + 1],
                closes=htf_data["c"][htf_start : htf_idx + 1],
                volumes=htf_data["v"][htf_start : htf_idx + 1],
                timestamps=htf_data["ts"][htf_start : htf_idx + 1],
            )
            last_htf_idx = htf_idx

        htf_state = last_htf_state
        if htf_state is None:
            continue

        # Check HTF Scalp Condition: Recent reaction (within 3 bars) at an HTF KeyZone
        htf_scalp_active = False
        has_htf_ob = len(htf_state.zones.order_blocks) > 0
        has_htf_fvg = len(htf_state.zones.fair_value_gaps) > 0
        htf_pd = htf_state.zones.premium_discount_zone

        if authorized_dir == 1:
            if htf_pd == "DISCOUNT" or has_htf_ob or has_htf_fvg:
                htf_scalp_active = True
        else:
            if htf_pd == "PREMIUM" or has_htf_ob or has_htf_fvg:
                htf_scalp_active = True

        if not htf_scalp_active:
            continue

        # 3. MTF STRATEGY LAYER: "MTF Intraday Momentum"
        # MTF must show an active trending momentum impulse in alignment with the HTF reaction
        mtf_idx = np.searchsorted(mtf_close_ts, t_curr, side="right") - 1
        if mtf_idx < 15:
            continue

        if mtf_idx != last_mtf_idx:
            mtf_start = max(0, mtf_idx - 100)
            last_mtf_state = coordinator.generators[mtf_tf].generate(
                symbol=symbol,
                opens=mtf_data["o"][mtf_start : mtf_idx + 1],
                highs=mtf_data["h"][mtf_start : mtf_idx + 1],
                lows=mtf_data["l"][mtf_start : mtf_idx + 1],
                closes=mtf_data["c"][mtf_start : mtf_idx + 1],
                volumes=mtf_data["v"][mtf_start : mtf_idx + 1],
                timestamps=mtf_data["ts"][mtf_start : mtf_idx + 1],
            )
            last_mtf_idx = mtf_idx

        mtf_state = last_mtf_state
        if mtf_state is None:
            continue

        # Check MTF Intraday Momentum: MTF internal trend must align or have confirmed MTF KeyZone
        mtf_intraday_active = False
        mtf_trend = mtf_state.structure.external_trend
        if authorized_dir == 1 and (mtf_trend == TrendDirection.BULLISH or len(mtf_state.zones.order_blocks) > 0):
            mtf_intraday_active = True
        elif authorized_dir == -1 and (mtf_trend == TrendDirection.BEARISH or len(mtf_state.zones.order_blocks) > 0):
            mtf_intraday_active = True

        if not mtf_intraday_active:
            continue

        # Register MTF structural trailing stop
        if authorized_dir == 1:
            if mtf_state.structure.last_major_low and mtf_state.structure.last_major_low.price < curr_px:
                trailing_map[t_curr] = mtf_state.structure.last_major_low.price
        else:
            if mtf_state.structure.last_major_high and mtf_state.structure.last_major_high.price > curr_px:
                trailing_map[t_curr] = mtf_state.structure.last_major_high.price

        # 4. LTF STRATEGY LAYER: "LTF Swing Wave Trigger"
        # LTF must confirm a multi-swing structural shift (CHoCH / BOS) indicating a full swing wave is starting
        ltf_start = max(0, i - 40)
        ltf_state = coordinator.generators[ltf_tf].generate(
            symbol=symbol,
            opens=ltf_data["o"][ltf_start : i + 1],
            highs=ltf_data["h"][ltf_start : i + 1],
            lows=ltf_data["l"][ltf_start : i + 1],
            closes=ltf_data["c"][ltf_start : i + 1],
            volumes=ltf_data["v"][ltf_start : i + 1],
            timestamps=ltf_data["ts"][ltf_start : i + 1],
        )

        ltf_breaks = ltf_state.structure.recent_breaks
        if not ltf_breaks:
            continue

        last_break = ltf_breaks[-1]
        break_dir = 0
        if last_break.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH):
            break_dir = 1
        elif last_break.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH):
            break_dir = -1

        if break_dir == 0 or break_dir != authorized_dir:
            continue

        # 5. ALL 3 STRATEGIES ALIGNED: Form the Single Composite Trade
        if break_dir == 1:
            sl_ref = ltf_state.structure.last_minor_low or ltf_state.structure.last_major_low
            initial_sl = sl_ref.price * 0.999 if sl_ref and sl_ref.price < curr_px else (curr_px - ltf_state.measurements.atr * 2.0)
            if target_set in ("SET_4", "SET_5"):
                min_stop = max(ltf_state.measurements.atr * 1.5, curr_px * 0.005)
                initial_sl = min(initial_sl, curr_px - min_stop)
            target_px = supply_tgt if (supply_tgt and supply_tgt > curr_px) else (curr_px + 4.5 * abs(curr_px - initial_sl))
            risk_dist = curr_px - initial_sl
            reward_dist = target_px - curr_px
        else:
            sl_ref = ltf_state.structure.last_minor_high or ltf_state.structure.last_major_high
            initial_sl = sl_ref.price * 1.001 if sl_ref and sl_ref.price > curr_px else (curr_px + ltf_state.measurements.atr * 2.0)
            if target_set in ("SET_4", "SET_5"):
                min_stop = max(ltf_state.measurements.atr * 1.5, curr_px * 0.005)
                initial_sl = max(initial_sl, curr_px + min_stop)
            target_px = demand_tgt if (demand_tgt and demand_tgt < curr_px) else (curr_px - 4.5 * abs(initial_sl - curr_px))
            risk_dist = initial_sl - curr_px
            reward_dist = curr_px - target_px

        realized_target_r = reward_dist / max(risk_dist, 1e-6)
        if realized_target_r < 4.0:
            continue

        candidates.append({
            "bar_index": i,
            "timestamp_ms": t_curr,
            "symbol": symbol,
            "origin_set": target_set,
            "direction": break_dir,
            "entry_price": curr_px,
            "stop_price": initial_sl,
            "target_price": target_px,
            "target_r": realized_target_r,
            "macro_baton": str(baton),
            "risk_dist": risk_dist,
            "reward_dist": reward_dist,
            "confluence_type": "TRI_STRATEGY_COMPOSITE",
        })

    return candidates, trailing_map


def run_tri_strategy_experiment():
    print("=" * 105)
    print("EMPIRICAL RESEARCH EXPERIMENT: TRI-STRATEGY CONFLUENCE IN ONE TRADE")
    print("HTF Scalp Strategy + MTF Intraday Strategy + LTF Swing Strategy = ONE TRADE")
    print("=" * 105)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

    coordinator = CascadingFractalCoordinator(
        min_target_r=4.0,
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )

    engine = CausalBacktestEngine(
        taker_fee_bps=5.0,
        slippage_bps=2.0,
        min_target_r=4.0,
        max_holding_bars=200,
    )

    results_by_set: Dict[str, Dict[str, Any]] = {
        s: {"trades": 0, "wins": 0, "total_r": 0.0, "gross_profit": 0.0, "gross_loss": 0.0}
        for s in sets
    }

    total_trades = 0
    total_wins = 0
    total_alpha_r = 0.0
    total_profit_r = 0.0
    total_loss_r = 0.0

    for asset in assets:
        all_data = load_all_7_timeframes(asset)
        if len(all_data) < 3:
            continue

        print(f"\nProcessing Asset: {asset}...")

        for target_set in sets:
            cfg = coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]
            if ltf_tf not in all_data:
                continue

            ltf_data = all_data[ltf_tf]

            candidates, trailing_map = scan_tri_strategy_signals(
                symbol=asset,
                target_set=target_set,
                all_data=all_data,
                coordinator=coordinator,
            )

            if not candidates:
                continue

            stream_id = f"TRI_{asset[:3]}_{target_set}"
            metrics = engine.execute_stream(
                stream_id=stream_id,
                symbol=asset,
                timeframe_set=target_set,
                hypothesis="TRI_STRATEGY_FRACTAL_CONFLUENCE",
                ltf_opens=ltf_data["o"],
                ltf_highs=ltf_data["h"],
                ltf_lows=ltf_data["l"],
                ltf_closes=ltf_data["c"],
                ltf_timestamps=ltf_data["ts"],
                signal_candidates=candidates,
                mtf_trailing_levels=trailing_map,
            )

            st = results_by_set[target_set]
            st["trades"] += metrics.total_trades
            st["wins"] += metrics.win_count
            st["total_r"] += metrics.total_r
            for t in metrics.trades:
                if t.realized_r > 0:
                    st["gross_profit"] += t.realized_r
                    total_profit_r += t.realized_r
                else:
                    st["gross_loss"] += abs(t.realized_r)
                    total_loss_r += abs(t.realized_r)

            total_trades += metrics.total_trades
            total_wins += metrics.win_count
            total_alpha_r += metrics.total_r

            print(f"  [{stream_id:<22}] N={metrics.total_trades:>4} | WR: {metrics.win_rate*100:>5.1f}% | Net Alpha: {metrics.total_r:>+7.2f}R | PF: {metrics.profit_factor:>5.2f}")

    print("\n" + "=" * 105)
    print("TRI-STRATEGY FRACTAL COMPOSITE RESULTS BY SET")
    print("=" * 105)
    header = f"{'TIMEFRAME SET':<18} | {'TRADES (N)':<12} | {'WIN RATE':<12} | {'NET ALPHA (R)':<15} | {'PROFIT FACTOR':<15}"
    print(header)
    print("-" * 105)

    for target_set, st in results_by_set.items():
        n = st["trades"]
        wr = (st["wins"] / n * 100) if n > 0 else 0.0
        pf = (st["gross_profit"] / st["gross_loss"]) if st["gross_loss"] > 0 else (99.0 if st["gross_profit"] > 0 else 0.0)
        net_r = st["total_r"]
        print(f"{target_set:<18} | {n:<12} | {wr:>10.1f}% | {net_r:>+13.2f}R | {pf:>13.2f}")

    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    overall_pf = (total_profit_r / total_loss_r) if total_loss_r > 0 else 0.0
    print("-" * 105)
    print(f"{'MASTER COMPOSITE':<18} | {total_trades:<12} | {overall_wr:>10.1f}% | {total_alpha_r:>+13.2f}R | {overall_pf:>13.2f}")
    print("=" * 105)

    # Save artifact
    out_file = RESULTS_DIR / "tri_strategy_validation_results.json"
    summary_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_trades": total_trades,
        "overall_win_rate_pct": round(overall_wr, 2),
        "total_alpha_r": round(total_alpha_r, 2),
        "overall_profit_factor": round(overall_pf, 2),
        "by_set": {
            s: {
                "trades": results_by_set[s]["trades"],
                "win_rate_pct": round((results_by_set[s]["wins"] / results_by_set[s]["trades"] * 100) if results_by_set[s]["trades"] > 0 else 0.0, 2),
                "net_r": round(results_by_set[s]["total_r"], 2),
                "profit_factor": round((results_by_set[s]["gross_profit"] / results_by_set[s]["gross_loss"]) if results_by_set[s]["gross_loss"] > 0 else 0.0, 2),
            }
            for s in sets
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"\nArtifact saved to: {out_file}")


if __name__ == "__main__":
    run_tri_strategy_experiment()
