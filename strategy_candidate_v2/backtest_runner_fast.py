"""
Optimized Backtest Runner for Multi-Asset / Multi-Timeframe Strategy.

Uses numpy arrays and binary search for efficient HTF/MTF/LTF synchronization.
"""

import os
import csv
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from bisect import bisect_right

from market_data.data_manager import DataManager
from market_intelligence.primitives import Candle
from strategy_candidate.indicators import SupertrendEngine, StochasticEngine
from market_intelligence.raw_swing_engine import RawSwingEngine, RawSwingConfig
from strategy_engine.news.news_provider import NullNewsProvider
from backtesting.friction_model import FrictionModel
from strategy_candidate_v2.strategy_engine import (
    StrategyEngine, TimeframeState, SetupState, TrailingPhase,
    ActivePosition, HighLowData,
)
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, ASSETS, load_candles


class FastBacktestRunner:
    """
    Optimized backtest runner using numpy arrays and binary search.
    """

    def __init__(self, starting_balance: float = 10000.0, risk_pct: float = 0.01):
        self.starting_balance = starting_balance
        self.risk_pct = risk_pct
        self.engine = StrategyEngine()
        self.friction_model = FrictionModel()
        self.swing_engine = RawSwingEngine(RawSwingConfig(left_bars=2, right_bars=2))

    def run_single(
        self,
        symbol: str,
        set_name: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
    ) -> Dict[str, Any]:
        """Run backtest for a single asset x set combination."""
        if len(htf_candles) < 50 or len(mtf_candles) < 50 or len(ltf_candles) < 50:
            return self._empty_result(symbol, set_name, "INSUFFICIENT_DATA")

        # Compute indicators
        htf_st = SupertrendEngine.calculate(htf_candles, 6, 5.0)
        htf_stoch = StochasticEngine.calculate(htf_candles, 25, 5, 3)
        htf_swings = self.swing_engine.detect(htf_candles)

        mtf_st = SupertrendEngine.calculate(mtf_candles, 6, 5.0)
        mtf_stoch = StochasticEngine.calculate(mtf_candles, 25, 5, 3)
        mtf_swings = self.swing_engine.detect(mtf_candles)

        ltf_st = SupertrendEngine.calculate(ltf_candles, 6, 5.0)
        ltf_stoch = StochasticEngine.calculate(ltf_candles, 25, 5, 3)
        ltf_swings = self.swing_engine.detect(ltf_candles)

        # Convert to numpy arrays for fast access
        htf_ts_arr = np.array([c.timestamp for c in htf_candles])
        mtf_ts_arr = np.array([c.timestamp for c in mtf_candles])
        ltf_ts_arr = np.array([c.timestamp for c in ltf_candles])

        htf_interval = int(htf_ts_arr[1] - htf_ts_arr[0]) if len(htf_ts_arr) > 1 else 0
        mtf_interval = int(mtf_ts_arr[1] - mtf_ts_arr[0]) if len(mtf_ts_arr) > 1 else 0
        ltf_interval = int(ltf_ts_arr[1] - ltf_ts_arr[0]) if len(ltf_ts_arr) > 1 else 0

        # Pre-extract indicator arrays
        htf_st_dir = np.array([s["direction"] for s in htf_st])
        htf_st_val = np.array([s["supertrend"] for s in htf_st])
        htf_k = np.array([s["k"] for s in htf_stoch])
        htf_d = np.array([s["d"] for s in htf_stoch])

        mtf_st_dir = np.array([s["direction"] for s in mtf_st])
        mtf_st_val = np.array([s["supertrend"] for s in mtf_st])
        mtf_k = np.array([s["k"] for s in mtf_stoch])
        mtf_d = np.array([s["d"] for s in mtf_stoch])

        ltf_st_dir = np.array([s["direction"] for s in ltf_st])
        ltf_st_val = np.array([s["supertrend"] for s in ltf_st])
        ltf_k = np.array([s["k"] for s in ltf_stoch])
        ltf_d = np.array([s["d"] for s in ltf_stoch])

        # State machines for both directions
        htf_states = {1: TimeframeState("HTF"), -1: TimeframeState("HTF")}
        mtf_states = {1: TimeframeState("MTF"), -1: TimeframeState("MTF")}
        ltf_states = {1: TimeframeState("LTF"), -1: TimeframeState("LTF")}

        balance = self.starting_balance
        trades = []
        active_position: Optional[ActivePosition] = None
        trade_counter = 0
        rejected_6r_count = 0
        news_filtered_count = 0
        valid_setups = 0

        # Pre-compute HTF/MTF close times for binary search
        htf_close_ts = htf_ts_arr + htf_interval
        mtf_close_ts = mtf_ts_arr + mtf_interval

        start_bar = 10
        num_ltf = len(ltf_candles)

        for i in range(start_bar, num_ltf):
            if balance <= 0:
                break

            ltf_bar = ltf_candles[i]
            ltf_close_time = int(ltf_ts_arr[i] + ltf_interval)

            # Binary search for HTF/MTF indices
            htf_idx = bisect_right(htf_close_ts, ltf_close_time) - 1
            mtf_idx = bisect_right(mtf_close_ts, ltf_close_time) - 1

            if htf_idx < 0:
                htf_idx = 0
            if mtf_idx < 0:
                mtf_idx = 0

            # Get current indicator values
            cur_htf_st_dir = int(htf_st_dir[htf_idx])
            cur_htf_st_val = float(htf_st_val[htf_idx])
            cur_htf_k = float(htf_k[htf_idx])
            cur_htf_d = float(htf_d[htf_idx])

            cur_mtf_st_dir = int(mtf_st_dir[mtf_idx])
            cur_mtf_st_val = float(mtf_st_val[mtf_idx])
            cur_mtf_k = float(mtf_k[mtf_idx])
            cur_mtf_d = float(mtf_d[mtf_idx])

            cur_ltf_st_dir = int(ltf_st_dir[i])
            cur_ltf_st_val = float(ltf_st_val[i])
            cur_ltf_k = float(ltf_k[i])
            cur_ltf_d = float(ltf_d[i])

            # Previous values
            prev_htf_k = float(htf_k[htf_idx - 1]) if htf_idx > 0 else cur_htf_k
            prev_htf_d = float(htf_d[htf_idx - 1]) if htf_idx > 0 else cur_htf_d
            prev_mtf_k = float(mtf_k[mtf_idx - 1]) if mtf_idx > 0 else cur_mtf_k
            prev_mtf_d = float(mtf_d[mtf_idx - 1]) if mtf_idx > 0 else cur_mtf_d
            prev_ltf_k = float(ltf_k[i - 1]) if i > 0 else cur_ltf_k
            prev_ltf_d = float(ltf_d[i - 1]) if i > 0 else cur_ltf_d

            # Manage active position
            if active_position is not None:
                self.engine.update_trailing(
                    active_position,
                    cur_ltf_st_val,
                    cur_mtf_st_val,
                    cur_htf_st_val,
                    ltf_close_time,
                )

                hl = HighLowData(high=ltf_bar.high, low=ltf_bar.low)
                should_exit, exit_reason, exit_price = self.engine.check_exit(active_position, hl)

                if should_exit:
                    if active_position.direction == 1:
                        fill_exit = self.friction_model.calculate_sell_fill(exit_price)
                        pnl_per_unit = fill_exit - active_position.fill_entry
                    else:
                        fill_exit = self.friction_model.calculate_buy_fill(exit_price)
                        pnl_per_unit = active_position.fill_entry - fill_exit

                    notional_exit = fill_exit * active_position.size
                    exit_fee = self.friction_model.calculate_fee(notional_exit)
                    gross_pnl = pnl_per_unit * active_position.size
                    net_pnl = gross_pnl - active_position.entry_fee - exit_fee

                    trade_record = {
                        "trade_id": active_position.trade_id,
                        "symbol": symbol,
                        "set": set_name,
                        "direction": "LONG" if active_position.direction == 1 else "SHORT",
                        "entry_ts": active_position.entry_ts,
                        "entry_price": active_position.entry_price,
                        "fill_entry": active_position.fill_entry,
                        "size": active_position.size,
                        "entry_fee": active_position.entry_fee,
                        "initial_sl": active_position.initial_sl,
                        "tp1": active_position.tp1,
                        "tp2": active_position.tp2,
                        "tp3": active_position.tp3,
                        "planned_rr": active_position.planned_rr,
                        "exit_ts": ltf_close_time,
                        "exit_price": exit_price,
                        "fill_exit": fill_exit,
                        "exit_reason": exit_reason,
                        "exit_fee": exit_fee,
                        "net_pnl": net_pnl,
                        "trailing_phase": active_position.trailing_phase.value,
                        "transitions": active_position.transition_log,
                    }
                    trades.append(trade_record)
                    balance += net_pnl
                    active_position = None

                continue

            # Update state machines for both directions
            for direction in [1, -1]:
                self.engine.update_timeframe_state(
                    htf_states[direction],
                    cur_htf_st_dir, cur_htf_st_val,
                    cur_htf_k, cur_htf_d,
                    prev_htf_k, prev_htf_d,
                    htf_swings, ltf_close_time, direction, is_ltf=False,
                )
                self.engine.update_timeframe_state(
                    mtf_states[direction],
                    cur_mtf_st_dir, cur_mtf_st_val,
                    cur_mtf_k, cur_mtf_d,
                    prev_mtf_k, prev_mtf_d,
                    mtf_swings, ltf_close_time, direction, is_ltf=False,
                )
                self.engine.update_timeframe_state(
                    ltf_states[direction],
                    cur_ltf_st_dir, cur_ltf_st_val,
                    cur_ltf_k, cur_ltf_d,
                    prev_ltf_k, prev_ltf_d,
                    ltf_swings, ltf_close_time, direction, is_ltf=True,
                )

            # Check for entry signals
            for direction in [1, -1]:
                if self.engine.check_entry(
                    htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                ):
                    valid_setups += 1

                    entry_price = ltf_bar.close
                    sl_price = cur_ltf_st_val
                    tp3_price = htf_states[direction].target_price
                    tp2_price = mtf_states[direction].target_price
                    tp1_price = ltf_states[direction].target_price

                    if tp3_price is None or tp2_price is None or tp1_price is None:
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                        )
                        continue

                    risk = abs(entry_price - sl_price)
                    if risk <= 0:
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                        )
                        continue

                    reward = abs(tp3_price - entry_price)
                    rr = reward / risk

                    if rr < 6.0:
                        rejected_6r_count += 1
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                        )
                        continue

                    is_blackout, _ = self.engine.news_provider.is_news_blackout(symbol, ltf_close_time)
                    if is_blackout:
                        news_filtered_count += 1
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                        )
                        continue

                    trade_counter += 1
                    fill_entry = (
                        self.friction_model.calculate_buy_fill(entry_price)
                        if direction == 1
                        else self.friction_model.calculate_sell_fill(entry_price)
                    )
                    dollar_risk = balance * self.risk_pct
                    position_size = dollar_risk / risk
                    notional_entry = fill_entry * position_size
                    entry_fee = self.friction_model.calculate_fee(notional_entry)

                    active_position = ActivePosition(
                        trade_id=f"{symbol}_{set_name}_{trade_counter}",
                        symbol=symbol,
                        set_name=set_name,
                        direction=direction,
                        entry_ts=ltf_close_time,
                        entry_price=entry_price,
                        fill_entry=fill_entry,
                        size=position_size,
                        entry_fee=entry_fee,
                        initial_sl=sl_price,
                        current_sl=sl_price,
                        tp1=tp1_price,
                        tp2=tp2_price,
                        tp3=tp3_price,
                        planned_rr=rr,
                    )

                    self.engine.reset_after_entry(
                        htf_states[direction], mtf_states[direction], ltf_states[direction], direction,
                    )
                    break

        return {
            "symbol": symbol,
            "set": set_name,
            "starting_balance": self.starting_balance,
            "final_balance": balance,
            "trades": trades,
            "valid_setups": valid_setups,
            "rejected_6r": rejected_6r_count,
            "news_filtered": news_filtered_count,
            "total_trades": len(trades),
        }

    def _empty_result(self, symbol: str, set_name: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "set": set_name,
            "starting_balance": self.starting_balance,
            "final_balance": self.starting_balance,
            "trades": [],
            "valid_setups": 0,
            "rejected_6r": 0,
            "news_filtered": 0,
            "total_trades": 0,
            "status": reason,
        }


def run_all_backtests(output_dir: str = None) -> List[Dict[str, Any]]:
    """Run backtests for all 18 asset x set combinations."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    runner = FastBacktestRunner(starting_balance=10000.0, risk_pct=0.01)
    all_results = []

    for symbol in ASSETS:
        for set_name, set_config in TIMEFRAME_SETS.items():
            print(f"\n{'='*60}")
            print(f"Running: {symbol} {set_name} ({set_config['style']})")
            print(f"  HTF={set_config['HTF']} MTF={set_config['MTF']} LTF={set_config['LTF']}")

            htf_candles = load_candles(symbol, set_config["HTF"])
            mtf_candles = load_candles(symbol, set_config["MTF"])
            ltf_candles = load_candles(symbol, set_config["LTF"])

            if htf_candles is None or mtf_candles is None or ltf_candles is None:
                print(f"  SKIPPED: Missing data")
                result = runner._empty_result(symbol, set_name, "MISSING_DATA")
                all_results.append(result)
                continue

            result = runner.run_single(symbol, set_name, htf_candles, mtf_candles, ltf_candles)
            all_results.append(result)

            print(f"  Trades: {result['total_trades']}")
            print(f"  Final Balance: ${result['final_balance']:.2f}")
            print(f"  Rejected <6R: {result['rejected_6r']}")
            print(f"  News Filtered: {result['news_filtered']}")

    _save_results(all_results, output_dir)
    return all_results


def _save_results(results: List[Dict[str, Any]], output_dir: str):
    """Save results to CSV and JSON."""
    ledger_path = os.path.join(output_dir, "trade_ledger.csv")
    with open(ledger_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "trade_id", "symbol", "set", "direction", "entry_ts", "entry_price",
            "fill_entry", "size", "entry_fee", "initial_sl", "tp1", "tp2", "tp3",
            "planned_rr", "exit_ts", "exit_price", "fill_exit", "exit_reason",
            "exit_fee", "net_pnl", "trailing_phase",
        ])
        for result in results:
            for trade in result["trades"]:
                writer.writerow([
                    trade["trade_id"], trade["symbol"], trade["set"], trade["direction"],
                    trade["entry_ts"], trade["entry_price"], trade["fill_entry"], trade["size"],
                    trade["entry_fee"], trade["initial_sl"], trade["tp1"], trade["tp2"], trade["tp3"],
                    trade["planned_rr"], trade["exit_ts"], trade["exit_price"], trade["fill_exit"],
                    trade["exit_reason"], trade["exit_fee"], trade["net_pnl"], trade["trailing_phase"],
                ])

    summary_path = os.path.join(output_dir, "summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["asset", "set", "total_trades", "final_balance", "net_pnl", "rejected_6r", "news_filtered", "valid_setups"])
        for result in results:
            net_pnl = result["final_balance"] - result["starting_balance"]
            writer.writerow([
                result["symbol"], result["set"], result["total_trades"],
                result["final_balance"], net_pnl, result["rejected_6r"],
                result["news_filtered"], result["valid_setups"],
            ])

    json_path = os.path.join(output_dir, "full_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}")


if __name__ == "__main__":
    run_all_backtests()
