"""
Product 04 — Research Laboratory: Vertical Slice 001 Runner
Executes BTCUSDT S3 (1D -> 4H -> 1H) Pullback Riding on genuine historical exchange data.
Performs Phase 5 (Empirical Backtest) and Phase 6 (MTF Trailing A/B Test).
"""

import os
import sys
import json
import statistics
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add repository root to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import CANONICAL_TIMEFRAME_SETS


def format_ts(ts: int) -> str:
    """Format timestamp (seconds or ms) to UTC date string."""
    if ts > 10**11:
        ts = ts / 1000.0
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def run_vertical_slice():
    print("================================================================================")
    print("      DAY 34 — VERTICAL SLICE 001: BTCUSDT S3 PULLBACK RIDING RESEARCH RUN      ")
    print("================================================================================\n")

    symbol = "BTC/USDT"
    set_id = "SET_3"
    tf_set = CANONICAL_TIMEFRAME_SETS[set_id]

    print(f"[1] Loading genuine historical market data for {symbol} ({set_id}: {tf_set.description})...")
    htf_candles = WarehouseLoader.load_history(symbol, tf_set.htf, limit=50000)
    mtf_candles = WarehouseLoader.load_history(symbol, tf_set.mtf, limit=50000)
    ltf_candles = WarehouseLoader.load_history(symbol, tf_set.ltf, limit=50000)

    print(f"  • HTF ({tf_set.htf}): {len(htf_candles)} candles loaded")
    print(f"  • MTF ({tf_set.mtf}): {len(mtf_candles)} candles loaded")
    print(f"  • LTF ({tf_set.ltf}): {len(ltf_candles)} candles loaded\n")

    # ---------------------------------------------------------
    # PHASE 5: BASELINE REPLAY (WITH MTF STRUCTURAL TRAILING)
    # ---------------------------------------------------------
    print("[2] Executing Phase 5 Empirical Replay (With MTF Structural Trailing)...")
    replayer_trailing = CausalReplayer(
        timeframe_set_id=set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=True,
        cache_htf_mtf=True
    )
    # Restrict hypotheses to Pullback Riding for this vertical slice
    replayer_trailing.strategy_coordinator.hypotheses = {
        "HYP_A_PULLBACK_RIDING": replayer_trailing.strategy_coordinator.hypotheses["HYP_A_PULLBACK_RIDING"]
    }

    res_trailing = replayer_trailing.run(
        symbol=symbol,
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )

    # ---------------------------------------------------------
    # PHASE 6: A/B TEST REPLAY (WITHOUT MTF STRUCTURAL TRAILING)
    # ---------------------------------------------------------
    print("[3] Executing Phase 6 A/B Replay (Fixed TP / No MTF Trailing)...")
    replayer_fixed = CausalReplayer(
        timeframe_set_id=set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=False,
        cache_htf_mtf=True
    )
    replayer_fixed.strategy_coordinator.hypotheses = {
        "HYP_A_PULLBACK_RIDING": replayer_fixed.strategy_coordinator.hypotheses["HYP_A_PULLBACK_RIDING"]
    }

    res_fixed = replayer_fixed.run(
        symbol=symbol,
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )

    # ---------------------------------------------------------
    # COMPOSE COMPREHENSIVE FORENSIC REPORT
    # ---------------------------------------------------------
    def extract_stats(res: Dict[str, Any]) -> Dict[str, Any]:
        metrics = res["metrics"]
        trades = res["closed_trades"]
        exits = res["exit_attribution"]
        
        r_multiples = [t.get("realized_rr", 0.0) for t in trades if t.get("realized_rr") is not None]
        pnl_usd = [t.get("realized_pnl", 0.0) for t in trades if t.get("realized_pnl") is not None]
        
        cumulative_r = sum(r_multiples) if r_multiples else 0.0
        median_r = statistics.median(r_multiples) if r_multiples else 0.0
        largest_win_r = max(r_multiples) if r_multiples else 0.0
        largest_win_usd = max(pnl_usd) if pnl_usd else 0.0
        largest_loss_r = min(r_multiples) if r_multiples else 0.0
        largest_loss_usd = min(pnl_usd) if pnl_usd else 0.0

        trade_count = metrics.get("total_trades", len(trades))
        win_rate = metrics.get("win_rate", 0.0)
        win_rate_pct = win_rate * 100.0 if isinstance(win_rate, (int, float)) else 0.0
        avg_r = metrics.get("average_r", 0.0)
        expectancy_r = metrics.get("expectancy_r", 0.0)
        profit_factor = metrics.get("profit_factor", 0.0)
        max_dd = metrics.get("max_drawdown_pct", 0.0)
        max_dd_pct = max_dd * 100.0 if isinstance(max_dd, (int, float)) else 0.0

        htf_tp_count = exits.get("HTF_TP", {}).get("trade_count", 0) if isinstance(exits.get("HTF_TP"), dict) else exits.get("HTF_TP", 0)
        ltf_sl_count = exits.get("INITIAL_LTF_SL", {}).get("trade_count", 0) if isinstance(exits.get("INITIAL_LTF_SL"), dict) else exits.get("INITIAL_LTF_SL", 0)
        mtf_trail_count = exits.get("MTF_STRUCTURAL_TRAIL", {}).get("trade_count", 0) if isinstance(exits.get("MTF_STRUCTURAL_TRAIL"), dict) else exits.get("MTF_STRUCTURAL_TRAIL", 0)

        return {
            "trade_count": trade_count,
            "win_rate_pct": win_rate_pct,
            "avg_r": avg_r,
            "median_r": median_r,
            "expectancy_r": expectancy_r,
            "profit_factor": profit_factor,
            "cumulative_r": cumulative_r,
            "max_drawdown_pct": max_dd_pct,
            "largest_win_r": largest_win_r,
            "largest_win_usd": largest_win_usd,
            "largest_loss_r": largest_loss_r,
            "largest_loss_usd": largest_loss_usd,
            "htf_tp_exits": htf_tp_count,
            "ltf_sl_exits": ltf_sl_count,
            "mtf_trail_exits": mtf_trail_count
        }

    stats_trailing = extract_stats(res_trailing)
    stats_fixed = extract_stats(res_fixed)

    start_date = format_ts(ltf_candles[0].timestamp)
    end_date = format_ts(ltf_candles[-1].timestamp)
    replayed_candles = res_trailing["replayed_candles_count"]
    suspended_count = res_trailing["suspended_intervals_count"]

    def fmt_val(v, decimals=2, suffix=""):
        if isinstance(v, (int, float)):
            return f"{v:.{decimals}f}{suffix}"
        return str(v)

    print("\n" + "="*80)
    print("                    PHASE 5: EMPIRICAL PERFORMANCE REPORT                      ")
    print("="*80)
    print(f"Asset:                       BTCUSDT")
    print(f"Timeframe Set:               S3 (1D -> 4H -> 1H)")
    print(f"Strategy Hypothesis:         Pullback Riding")
    print(f"Date Range Tested:           {start_date} to {end_date}")
    print(f"Replayed 1H Candles:         {replayed_candles:,}")
    print(f"Suspended Intervals (Gaps):  {suspended_count}")
    print(f"Total Trades Executed:       {stats_trailing['trade_count']}")
    print(f"Win Rate:                    {fmt_val(stats_trailing['win_rate_pct'], 2, '%')}")
    print(f"Average R:                   {fmt_val(stats_trailing['avg_r'], 2, 'R')}")
    print(f"Median R:                    {fmt_val(stats_trailing['median_r'], 2, 'R')}")
    print(f"Expectancy:                  {fmt_val(stats_trailing['expectancy_r'], 2, 'R per trade')}")
    print(f"Profit Factor:               {fmt_val(stats_trailing['profit_factor'])}")
    print(f"Cumulative R:                {fmt_val(stats_trailing['cumulative_r'], 2, 'R')}")
    print(f"Maximum Drawdown:            {fmt_val(stats_trailing['max_drawdown_pct'], 2, '%')}")
    print(f"Largest Win:                 +{fmt_val(stats_trailing['largest_win_r'], 2, 'R')} (${stats_trailing['largest_win_usd']:,.2f})")
    print(f"Largest Loss:                {fmt_val(stats_trailing['largest_loss_r'], 2, 'R')} (${stats_trailing['largest_loss_usd']:,.2f})")
    print(f"Exit Attribution:")
    print(f"  • HTF Take Profit (TP):    {stats_trailing['htf_tp_exits']}")
    print(f"  • Initial LTF Stop (SL):   {stats_trailing['ltf_sl_exits']}")
    print(f"  • MTF Structural Trailing: {stats_trailing['mtf_trail_exits']}")

    print("\n" + "="*80)
    print("                    PHASE 6: MTF TRAILING STOP A/B TEST                         ")
    print("="*80)
    print(f"{'Metric':<25} | {'Stream A: Fixed TP (No Trail)':<30} | {'Stream B: MTF Trailing (Canonical)':<30}")
    print("-" * 92)
    print(f"{'Trade Count':<25} | {stats_fixed['trade_count']:<30} | {stats_trailing['trade_count']:<30}")
    print(f"{'Win Rate':<25} | {fmt_val(stats_fixed['win_rate_pct'], 2, '%'):<30} | {fmt_val(stats_trailing['win_rate_pct'], 2, '%'):<30}")
    print(f"{'Average R':<25} | {fmt_val(stats_fixed['avg_r'], 2, 'R'):<30} | {fmt_val(stats_trailing['avg_r'], 2, 'R'):<30}")
    print(f"{'Expectancy':<25} | {fmt_val(stats_fixed['expectancy_r'], 2, 'R'):<30} | {fmt_val(stats_trailing['expectancy_r'], 2, 'R'):<30}")
    print(f"{'Profit Factor':<25} | {fmt_val(stats_fixed['profit_factor']):<30} | {fmt_val(stats_trailing['profit_factor']):<30}")
    print(f"{'Max Drawdown':<25} | {fmt_val(stats_fixed['max_drawdown_pct'], 2, '%'):<30} | {fmt_val(stats_trailing['max_drawdown_pct'], 2, '%'):<30}")
    print(f"{'Cumulative R':<25} | {fmt_val(stats_fixed['cumulative_r'], 2, 'R'):<30} | {fmt_val(stats_trailing['cumulative_r'], 2, 'R'):<30}")
    print(f"{'HTF TP Exits':<25} | {stats_fixed['htf_tp_exits']:<30} | {stats_trailing['htf_tp_exits']:<30}")
    print(f"{'Initial LTF SL Exits':<25} | {stats_fixed['ltf_sl_exits']:<30} | {stats_trailing['ltf_sl_exits']:<30}")
    print(f"{'MTF Trailing Exits':<25} | {stats_fixed['mtf_trail_exits']:<30} | {stats_trailing['mtf_trail_exits']:<30}")
    print("="*80 + "\n")

    return {
        "date_range": {"start": start_date, "end": end_date},
        "replayed_candles": replayed_candles,
        "suspended_intervals": suspended_count,
        "trailing": stats_trailing,
        "fixed": stats_fixed
    }


if __name__ == "__main__":
    run_vertical_slice()
