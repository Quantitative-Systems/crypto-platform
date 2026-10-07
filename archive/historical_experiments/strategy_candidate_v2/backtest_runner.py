"""
Backtest Runner for Multi-Asset / Multi-Timeframe Strategy.

Runs the strategy across all 18 asset x set combinations.
Handles HTF/MTF/LTF synchronization, position management, and trade logging.
"""

import os
import csv
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

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


class BacktestRunner:
    """
    Runs the complete backtest for a single asset x set combination.
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
        """
        Run backtest for a single asset x set combination.
        Evaluates both LONG and SHORT directions simultaneously.
        """
        if len(htf_candles) < 50 or len(mtf_candles) < 50 or len(ltf_candles) < 50:
            return self._empty_result(symbol, set_name, "INSUFFICIENT_DATA")

        # Compute indicators for all timeframes
        htf_st = SupertrendEngine.calculate(htf_candles, 6, 5.0)
        htf_stoch = StochasticEngine.calculate(htf_candles, 25, 5, 3)
        htf_swings = self.swing_engine.detect(htf_candles)

        mtf_st = SupertrendEngine.calculate(mtf_candles, 6, 5.0)
        mtf_stoch = StochasticEngine.calculate(mtf_candles, 25, 5, 3)
        mtf_swings = self.swing_engine.detect(mtf_candles)

        ltf_st = SupertrendEngine.calculate(ltf_candles, 6, 5.0)
        ltf_stoch = StochasticEngine.calculate(ltf_candles, 25, 5, 3)
        ltf_swings = self.swing_engine.detect(ltf_candles)

        # Get intervals
        htf_interval = htf_candles[1].timestamp - htf_candles[0].timestamp if len(htf_candles) > 1 else 0
        mtf_interval = mtf_candles[1].timestamp - mtf_candles[0].timestamp if len(mtf_candles) > 1 else 0
        ltf_interval = ltf_candles[1].timestamp - ltf_candles[0].timestamp if len(ltf_candles) > 1 else 0

        # State machines for both directions
        # direction=1 (LONG), direction=-1 (SHORT)
        htf_states = {1: TimeframeState("HTF"), -1: TimeframeState("HTF")}
        mtf_states = {1: TimeframeState("MTF"), -1: TimeframeState("MTF")}
        ltf_states = {1: TimeframeState("LTF"), -1: TimeframeState("LTF")}

        balance = self.starting_balance
        trades = []
        active_position: Optional[ActivePosition] = None
        trade_counter = 0

        # Tracking for rejected setups
        rejected_6r_count = 0
        news_filtered_count = 0
        valid_setups = 0

        # Index tracking for HTF/MTF synchronization
        htf_idx = 0
        mtf_idx = 0

        # Start from bar 10 to have some history
        start_bar = 10

        for i in range(start_bar, len(ltf_candles)):
            if balance <= 0:
                break

            ltf_bar = ltf_candles[i]
            ltf_close_time = ltf_bar.timestamp + ltf_interval

            # Advance HTF index: find the latest HTF candle that has CLOSED by ltf_close_time
            while htf_idx + 1 < len(htf_candles) and (htf_candles[htf_idx + 1].timestamp + htf_interval) <= ltf_close_time:
                htf_idx += 1

            # Advance MTF index
            while mtf_idx + 1 < len(mtf_candles) and (mtf_candles[mtf_idx + 1].timestamp + mtf_interval) <= ltf_close_time:
                mtf_idx += 1

            # Get current indicator values
            cur_htf_st = htf_st[htf_idx]
            cur_htf_stoch = htf_stoch[htf_idx]
            cur_mtf_st = mtf_st[mtf_idx]
            cur_mtf_stoch = mtf_stoch[mtf_idx]
            cur_ltf_st = ltf_st[i]
            cur_ltf_stoch = ltf_stoch[i]

            # Previous values for crossover detection
            prev_htf_stoch = htf_stoch[htf_idx - 1] if htf_idx > 0 else cur_htf_stoch
            prev_mtf_stoch = mtf_stoch[mtf_idx - 1] if mtf_idx > 0 else cur_mtf_stoch
            prev_ltf_stoch = ltf_stoch[i - 1] if i > 0 else cur_ltf_stoch

            # Manage active position
            if active_position is not None:
                # Update trailing stop
                self.engine.update_trailing(
                    active_position,
                    cur_ltf_st["supertrend"],
                    cur_mtf_st["supertrend"],
                    cur_htf_st["supertrend"],
                    ltf_close_time,
                )

                # Check exit
                hl = HighLowData(high=ltf_bar.high, low=ltf_bar.low)
                should_exit, exit_reason, exit_price = self.engine.check_exit(active_position, hl)

                if should_exit:
                    # Calculate P&L
                    if active_position.direction == 1:  # LONG
                        fill_exit = self.friction_model.calculate_sell_fill(exit_price)
                        pnl_per_unit = fill_exit - active_position.fill_entry
                    else:  # SHORT
                        fill_exit = self.friction_model.calculate_buy_fill(exit_price)
                        pnl_per_unit = active_position.fill_entry - fill_exit

                    notional_exit = fill_exit * active_position.size
                    exit_fee = self.friction_model.calculate_fee(notional_exit)
                    gross_pnl = pnl_per_unit * active_position.size
                    net_pnl = gross_pnl - active_position.entry_fee - exit_fee
                    realized_r = net_pnl / (active_position.initial_sl - active_position.fill_entry) / active_position.size if active_position.fill_entry != active_position.initial_sl else 0

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
                        "realized_r": realized_r,
                        "trailing_phase": active_position.trailing_phase.value,
                        "transitions": active_position.transition_log,
                    }
                    trades.append(trade_record)
                    balance += net_pnl
                    active_position = None

                continue  # Skip entry logic while in position

            # Update state machines for both directions
            for direction in [1, -1]:
                self.engine.update_timeframe_state(
                    htf_states[direction],
                    cur_htf_st["direction"],
                    cur_htf_st["supertrend"],
                    cur_htf_stoch["k"],
                    cur_htf_stoch["d"],
                    prev_htf_stoch["k"],
                    prev_htf_stoch["d"],
                    htf_swings,
                    ltf_close_time,
                    direction,
                    is_ltf=False,
                )
                self.engine.update_timeframe_state(
                    mtf_states[direction],
                    cur_mtf_st["direction"],
                    cur_mtf_st["supertrend"],
                    cur_mtf_stoch["k"],
                    cur_mtf_stoch["d"],
                    prev_mtf_stoch["k"],
                    prev_mtf_stoch["d"],
                    mtf_swings,
                    ltf_close_time,
                    direction,
                    is_ltf=False,
                )
                self.engine.update_timeframe_state(
                    ltf_states[direction],
                    cur_ltf_st["direction"],
                    cur_ltf_st["supertrend"],
                    cur_ltf_stoch["k"],
                    cur_ltf_stoch["d"],
                    prev_ltf_stoch["k"],
                    prev_ltf_stoch["d"],
                    ltf_swings,
                    ltf_close_time,
                    direction,
                    is_ltf=True,
                )

            # Check for entry signals (both directions)
            for direction in [1, -1]:
                if self.engine.check_entry(
                    htf_states[direction],
                    mtf_states[direction],
                    ltf_states[direction],
                    direction,
                ):
                    valid_setups += 1

                    # Calculate entry parameters
                    entry_price = ltf_bar.close
                    sl_price = cur_ltf_st["supertrend"]
                    tp3_price = htf_states[direction].target_price
                    tp2_price = mtf_states[direction].target_price
                    tp1_price = ltf_states[direction].target_price

                    # Validate targets
                    if tp3_price is None or tp2_price is None or tp1_price is None:
                        # Cannot calculate RR without targets
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction
                        )
                        continue

                    # Calculate risk and RR
                    risk = abs(entry_price - sl_price)
                    if risk <= 0:
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction
                        )
                        continue

                    reward = abs(tp3_price - entry_price)
                    rr = reward / risk

                    # 6R filter
                    if rr < 6.0:
                        rejected_6r_count += 1
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction
                        )
                        continue

                    # News filter
                    is_blackout, _ = self.engine.news_provider.is_news_blackout(
                        symbol, ltf_close_time
                    )
                    if is_blackout:
                        news_filtered_count += 1
                        self.engine.reset_after_entry(
                            htf_states[direction], mtf_states[direction], ltf_states[direction], direction
                        )
                        continue

                    # ENTER TRADE
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

                    # Reset states
                    self.engine.reset_after_entry(
                        htf_states[direction], mtf_states[direction], ltf_states[direction], direction
                    )

                    # Only take one signal per bar
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

    runner = BacktestRunner(starting_balance=10000.0, risk_pct=0.01)
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

    # Save results
    _save_results(all_results, output_dir)
    return all_results


def _save_results(results: List[Dict[str, Any]], output_dir: str):
    """Save results to CSV and JSON."""
    # Save trade ledger
    ledger_path = os.path.join(output_dir, "trade_ledger.csv")
    with open(ledger_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "trade_id", "symbol", "set", "direction", "entry_ts", "entry_price",
            "fill_entry", "size", "entry_fee", "initial_sl", "tp1", "tp2", "tp3",
            "planned_rr", "exit_ts", "exit_price", "fill_exit", "exit_reason",
            "exit_fee", "net_pnl", "realized_r", "trailing_phase",
        ])
        for result in results:
            for trade in result["trades"]:
                writer.writerow([
                    trade["trade_id"],
                    trade["symbol"],
                    trade["set"],
                    trade["direction"],
                    trade["entry_ts"],
                    trade["entry_price"],
                    trade["fill_entry"],
                    trade["size"],
                    trade["entry_fee"],
                    trade["initial_sl"],
                    trade["tp1"],
                    trade["tp2"],
                    trade["tp3"],
                    trade["planned_rr"],
                    trade["exit_ts"],
                    trade["exit_price"],
                    trade["fill_exit"],
                    trade["exit_reason"],
                    trade["exit_fee"],
                    trade["net_pnl"],
                    trade["realized_r"],
                    trade["trailing_phase"],
                ])

    # Save summary
    summary_path = os.path.join(output_dir, "summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "asset", "set", "total_trades", "final_balance", "net_pnl",
            "rejected_6r", "news_filtered", "valid_setups",
        ])
        for result in results:
            net_pnl = result["final_balance"] - result["starting_balance"]
            writer.writerow([
                result["symbol"],
                result["set"],
                result["total_trades"],
                result["final_balance"],
                net_pnl,
                result["rejected_6r"],
                result["news_filtered"],
                result["valid_setups"],
            ])

    # Save full JSON
    json_path = os.path.join(output_dir, "full_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}")
    print(f"  Trade ledger: {ledger_path}")
    print(f"  Summary: {summary_path}")
    print(f"  Full JSON: {json_path}")


if __name__ == "__main__":
    run_all_backtests()
