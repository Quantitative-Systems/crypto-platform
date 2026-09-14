"""
Final optimized backtest runner with pre-computed lookups.
"""

import os
import sys
import csv
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from bisect import bisect_right

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.data_manager import DataManager
from market_intelligence.primitives import Candle, SwingType
from strategy_candidate_v2.fast_indicators import compute_indicators_fast
from strategy_engine.news.news_provider import NullNewsProvider
from backtesting.friction_model import FrictionModel
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, ASSETS, load_candles


class SwingCache:
    """Pre-computed swing lookup for O(1) target extraction."""
    def __init__(self, swings: List, candles: List[Candle]):
        self.high_targets = np.full(len(candles), np.nan)
        self.low_targets = np.full(len(candles), np.nan)
        self._build(candles, swings)

    def _build(self, candles: List[Candle], swings: List):
        """Build pre-computed arrays."""
        ts_arr = np.array([c.timestamp for c in candles])
        last_high = np.nan
        last_low = np.nan
        swing_idx = 0
        # Sort swings by confirmation_timestamp
        sorted_swings = sorted(swings, key=lambda s: s.confirmation_timestamp)

        for i in range(len(candles)):
            current_ts = candles[i].timestamp
            # Process all swings confirmed at or before this timestamp
            while swing_idx < len(sorted_swings) and sorted_swings[swing_idx].confirmation_timestamp <= current_ts:
                sw = sorted_swings[swing_idx]
                if sw.swing_type in (SwingType.HIGH, SwingType.SWING_HIGH):
                    last_high = sw.price
                elif sw.swing_type in (SwingType.LOW, SwingType.SWING_LOW):
                    last_low = sw.price
                swing_idx += 1
            self.high_targets[i] = last_high
            self.low_targets[i] = last_low

    def get_target(self, candle_idx: int, direction: int) -> Optional[float]:
        if direction == 1:  # Bullish -> need HIGH
            val = self.high_targets[candle_idx]
            return float(val) if not np.isnan(val) else None
        else:  # Bearish -> need LOW
            val = self.low_targets[candle_idx]
            return float(val) if not np.isnan(val) else None


def compute_all_indicators(candles: List[Candle]):
    """Compute indicators and return numpy arrays + swing cache."""
    from market_intelligence.raw_swing_engine import RawSwingEngine, RawSwingConfig
    ind = compute_indicators_fast(candles)
    swing_engine = RawSwingEngine(RawSwingConfig(left_bars=2, right_bars=2))
    swings = swing_engine.detect(candles)
    swing_cache = SwingCache(swings, candles)
    ind["swing_cache"] = swing_cache
    return ind


class StateMachine:
    """Lightweight state machine for a single timeframe."""
    __slots__ = ['state', 'peak_reached', 'pullback_reached', 'target_price', 'condition_met_ts']

    def __init__(self):
        self.state = 'IDLE'
        self.peak_reached = False
        self.pullback_reached = False
        self.target_price = None
        self.condition_met_ts = None


def update_state(sm: StateMachine, st_dir: int, k: float, d: float,
                 prev_k: float, prev_d: float, direction: int,
                 is_ltf: bool, swing_cache: SwingCache, candle_idx: int):
    """Update state machine."""
    STOCH_HIGH = 75.0
    STOCH_LOW = 25.0

    if direction == 1:  # BULLISH
        if st_dir != 1:
            sm.state = 'IDLE'
            sm.peak_reached = False
            sm.pullback_reached = False
            return

        if sm.state == 'IDLE':
            if k >= STOCH_HIGH:
                sm.state = 'WAITING_PEAK'
                sm.peak_reached = True
        elif sm.state == 'WAITING_PEAK':
            if k <= STOCH_LOW:
                sm.state = 'WAITING_PULLBACK'
                sm.pullback_reached = True
        elif sm.state == 'WAITING_PULLBACK':
            if st_dir == 1:
                if is_ltf:
                    sm.state = 'WAITING_CROSSOVER'
                else:
                    sm.state = 'READY'
                    sm.condition_met_ts = candle_idx
                    sm.target_price = swing_cache.get_target(candle_idx, direction)
            else:
                sm.state = 'IDLE'
                sm.peak_reached = False
                sm.pullback_reached = False
        elif sm.state == 'WAITING_CROSSOVER':
            if prev_k <= prev_d and k > d:
                if st_dir == 1:
                    sm.state = 'READY'
                    sm.condition_met_ts = candle_idx
                    sm.target_price = swing_cache.get_target(candle_idx, direction)
                else:
                    sm.state = 'IDLE'
                    sm.peak_reached = False
                    sm.pullback_reached = False
            elif k >= STOCH_HIGH:
                sm.state = 'WAITING_PEAK'
        elif sm.state == 'READY':
            if k >= STOCH_HIGH:
                sm.state = 'WAITING_PEAK'
    else:  # BEARISH
        if st_dir != -1:
            sm.state = 'IDLE'
            sm.peak_reached = False
            sm.pullback_reached = False
            return

        if sm.state == 'IDLE':
            if k <= STOCH_LOW:
                sm.state = 'WAITING_PEAK'
                sm.peak_reached = True
        elif sm.state == 'WAITING_PEAK':
            if k >= STOCH_HIGH:
                sm.state = 'WAITING_PULLBACK'
                sm.pullback_reached = True
        elif sm.state == 'WAITING_PULLBACK':
            if st_dir == -1:
                if is_ltf:
                    sm.state = 'WAITING_CROSSOVER'
                else:
                    sm.state = 'READY'
                    sm.condition_met_ts = candle_idx
                    sm.target_price = swing_cache.get_target(candle_idx, direction)
            else:
                sm.state = 'IDLE'
                sm.peak_reached = False
                sm.pullback_reached = False
        elif sm.state == 'WAITING_CROSSOVER':
            if prev_k >= prev_d and k < d:
                if st_dir == -1:
                    sm.state = 'READY'
                    sm.condition_met_ts = candle_idx
                    sm.target_price = swing_cache.get_target(candle_idx, direction)
                else:
                    sm.state = 'IDLE'
                    sm.peak_reached = False
                    sm.pullback_reached = False
            elif k <= STOCH_LOW:
                sm.state = 'WAITING_PEAK'
        elif sm.state == 'READY':
            if k <= STOCH_LOW:
                sm.state = 'WAITING_PEAK'


def run_single_set(symbol: str, set_name: str, htf_candles: List[Candle],
                   mtf_candles: List[Candle], ltf_candles: List[Candle]) -> Dict[str, Any]:
    """Run backtest for a single asset x set."""
    starting_balance = 10000.0
    risk_pct = 0.01
    friction = FrictionModel()

    if len(htf_candles) < 50 or len(mtf_candles) < 50 or len(ltf_candles) < 50:
        return {"symbol": symbol, "set": set_name, "starting_balance": starting_balance,
                "final_balance": starting_balance, "trades": [], "total_trades": 0,
                "valid_setups": 0, "rejected_6r": 0, "news_filtered": 0}

    # Compute indicators
    htf = compute_all_indicators(htf_candles)
    mtf = compute_all_indicators(mtf_candles)
    ltf = compute_all_indicators(ltf_candles)

    htf_close_ts = htf["ts"] + htf["interval"]
    mtf_close_ts = mtf["ts"] + mtf["interval"]

    # State machines
    htf_sm = {1: StateMachine(), -1: StateMachine()}
    mtf_sm = {1: StateMachine(), -1: StateMachine()}
    ltf_sm = {1: StateMachine(), -1: StateMachine()}

    balance = starting_balance
    trades = []
    active_pos = None
    trade_counter = 0
    rejected_6r = 0
    news_filtered = 0
    valid_setups = 0

    num_ltf = len(ltf_candles)
    ltf_high = ltf["high"]
    ltf_low = ltf["low"]
    ltf_close = ltf["close"]
    ltf_ts = ltf["ts"]

    for i in range(10, num_ltf):
        if balance <= 0:
            break

        ltf_close_time = int(ltf_ts[i] + ltf["interval"])

        # Binary search for HTF/MTF indices
        htf_idx = bisect_right(htf_close_ts, ltf_close_time) - 1
        mtf_idx = bisect_right(mtf_close_ts, ltf_close_time) - 1
        if htf_idx < 0: htf_idx = 0
        if mtf_idx < 0: mtf_idx = 0

        # Current values
        hdi = int(htf["st_dir"][htf_idx])
        hdv = float(htf["st_val"][htf_idx])
        hk = float(htf["k"][htf_idx])
        hd = float(htf["d"][htf_idx])
        mdi = int(mtf["st_dir"][mtf_idx])
        mdv = float(mtf["st_val"][mtf_idx])
        mk = float(mtf["k"][mtf_idx])
        md = float(mtf["d"][mtf_idx])
        ldi = int(ltf["st_dir"][i])
        ldv = float(ltf["st_val"][i])
        lk = float(ltf["k"][i])
        ld = float(ltf["d"][i])

        # Previous values
        phk = float(htf["k"][htf_idx - 1]) if htf_idx > 0 else hk
        phd = float(htf["d"][htf_idx - 1]) if htf_idx > 0 else hd
        pmk = float(mtf["k"][mtf_idx - 1]) if mtf_idx > 0 else mk
        pmd = float(mtf["d"][mtf_idx - 1]) if mtf_idx > 0 else md
        plk = float(ltf["k"][i - 1]) if i > 0 else lk
        pld = float(ltf["d"][i - 1]) if i > 0 else ld

        # Manage active position
        if active_pos is not None:
            direction = active_pos["direction"]
            # Update trailing
            if direction == 1:  # LONG
                if active_pos["phase"] == 1:
                    if ldv > active_pos["sl"]:
                        active_pos["sl"] = ldv
                    if ltf_high[i] >= active_pos["tp1"]:
                        active_pos["phase"] = 2
                elif active_pos["phase"] == 2:
                    if mdv >= active_pos["sl"]:
                        active_pos["sl"] = mdv
                        active_pos["phase"] = 3
                elif active_pos["phase"] == 3:
                    if mdv > active_pos["sl"]:
                        active_pos["sl"] = mdv
                    if ltf_high[i] >= active_pos["tp2"]:
                        active_pos["phase"] = 4
                elif active_pos["phase"] == 4:
                    if hdv >= active_pos["sl"]:
                        active_pos["sl"] = hdv
                        active_pos["phase"] = 5
                elif active_pos["phase"] == 5:
                    if hdv > active_pos["sl"]:
                        active_pos["sl"] = hdv

                # Check exit (adverse first)
                if ltf_low[i] <= active_pos["sl"]:
                    fill_exit = friction.calculate_sell_fill(active_pos["sl"])
                    pnl = (fill_exit - active_pos["fill_entry"]) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({
                        "trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "LONG", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["sl"], "fill_exit": fill_exit,
                        "exit_reason": "SL", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"],
                    })
                    balance += net_pnl
                    active_pos = None
                elif ltf_high[i] >= active_pos["tp3"]:
                    fill_exit = friction.calculate_sell_fill(active_pos["tp3"])
                    pnl = (fill_exit - active_pos["fill_entry"]) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({
                        "trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "LONG", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["tp3"], "fill_exit": fill_exit,
                        "exit_reason": "TP3", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"],
                    })
                    balance += net_pnl
                    active_pos = None
            else:  # SHORT
                if active_pos["phase"] == 1:
                    if ldv < active_pos["sl"]:
                        active_pos["sl"] = ldv
                    if ltf_low[i] <= active_pos["tp1"]:
                        active_pos["phase"] = 2
                elif active_pos["phase"] == 2:
                    if mdv <= active_pos["sl"]:
                        active_pos["sl"] = mdv
                        active_pos["phase"] = 3
                elif active_pos["phase"] == 3:
                    if mdv < active_pos["sl"]:
                        active_pos["sl"] = mdv
                    if ltf_low[i] <= active_pos["tp2"]:
                        active_pos["phase"] = 4
                elif active_pos["phase"] == 4:
                    if hdv <= active_pos["sl"]:
                        active_pos["sl"] = hdv
                        active_pos["phase"] = 5
                elif active_pos["phase"] == 5:
                    if hdv < active_pos["sl"]:
                        active_pos["sl"] = hdv

                if ltf_high[i] >= active_pos["sl"]:
                    fill_exit = friction.calculate_buy_fill(active_pos["sl"])
                    pnl = (active_pos["fill_entry"] - fill_exit) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({
                        "trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "SHORT", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["sl"], "fill_exit": fill_exit,
                        "exit_reason": "SL", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"],
                    })
                    balance += net_pnl
                    active_pos = None
                elif ltf_low[i] <= active_pos["tp3"]:
                    fill_exit = friction.calculate_buy_fill(active_pos["tp3"])
                    pnl = (active_pos["fill_entry"] - fill_exit) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({
                        "trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "SHORT", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["tp3"], "fill_exit": fill_exit,
                        "exit_reason": "TP3", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"],
                    })
                    balance += net_pnl
                    active_pos = None

            continue

        # Update state machines
        for direction in [1, -1]:
            update_state(htf_sm[direction], hdi, hk, hd, phk, phd, direction, False,
                         htf["swing_cache"], htf_idx)
            update_state(mtf_sm[direction], mdi, mk, md, pmk, pmd, direction, False,
                         mtf["swing_cache"], mtf_idx)
            update_state(ltf_sm[direction], ldi, lk, ld, plk, pld, direction, True,
                         ltf["swing_cache"], i)

        # Check entry signals
        for direction in [1, -1]:
            if (htf_sm[direction].state == 'READY' and
                mtf_sm[direction].state == 'READY' and
                ltf_sm[direction].state == 'READY'):

                valid_setups += 1
                entry_price = float(ltf_close[i])
                sl_price = ldv
                tp3 = htf_sm[direction].target_price
                tp2 = mtf_sm[direction].target_price
                tp1 = ltf_sm[direction].target_price

                if tp3 is None or tp2 is None or tp1 is None:
                    htf_sm[direction].state = 'IDLE'
                    mtf_sm[direction].state = 'IDLE'
                    ltf_sm[direction].state = 'IDLE'
                    continue

                risk = abs(entry_price - sl_price)
                if risk <= 0:
                    htf_sm[direction].state = 'IDLE'
                    mtf_sm[direction].state = 'IDLE'
                    ltf_sm[direction].state = 'IDLE'
                    continue

                if direction == 1:
                    reward = tp3 - entry_price
                else:
                    reward = entry_price - tp3

                if reward <= 0:
                    rejected_6r += 1
                    htf_sm[direction].state = 'IDLE'
                    mtf_sm[direction].state = 'IDLE'
                    ltf_sm[direction].state = 'IDLE'
                    continue

                rr = reward / risk

                if rr < 6.0:
                    rejected_6r += 1
                    htf_sm[direction].state = 'IDLE'
                    mtf_sm[direction].state = 'IDLE'
                    ltf_sm[direction].state = 'IDLE'
                    continue

                # Enter trade
                trade_counter += 1
                if direction == 1:
                    fill_entry = friction.calculate_buy_fill(entry_price)
                else:
                    fill_entry = friction.calculate_sell_fill(entry_price)
                dollar_risk = balance * risk_pct
                position_size = dollar_risk / risk
                notional_entry = fill_entry * position_size
                entry_fee = friction.calculate_fee(notional_entry)

                active_pos = {
                    "id": f"{symbol}_{set_name}_{trade_counter}",
                    "direction": direction,
                    "entry_ts": ltf_close_time,
                    "entry_price": entry_price,
                    "fill_entry": fill_entry,
                    "size": position_size,
                    "entry_fee": entry_fee,
                    "initial_sl": sl_price,
                    "sl": sl_price,
                    "tp1": tp1,
                    "tp2": tp2,
                    "tp3": tp3,
                    "planned_rr": rr,
                    "phase": 1,
                }

                htf_sm[direction].state = 'IDLE'
                mtf_sm[direction].state = 'IDLE'
                ltf_sm[direction].state = 'IDLE'
                break

    return {
        "symbol": symbol, "set": set_name, "starting_balance": starting_balance,
        "final_balance": balance, "trades": trades, "total_trades": len(trades),
        "valid_setups": valid_setups, "rejected_6r": rejected_6r, "news_filtered": news_filtered,
    }


def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(output_dir, exist_ok=True)
    all_results = []

    for symbol in ASSETS:
        for set_name, sc in TIMEFRAME_SETS.items():
            print(f"\nRunning: {symbol} {set_name} ({sc['style']})")
            htf = load_candles(symbol, sc["HTF"])
            mtf = load_candles(symbol, sc["MTF"])
            ltf = load_candles(symbol, sc["LTF"])

            if htf is None or mtf is None or ltf is None:
                print(f"  SKIPPED: Missing data")
                all_results.append({"symbol": symbol, "set": set_name, "starting_balance": 10000,
                                    "final_balance": 10000, "trades": [], "total_trades": 0,
                                    "valid_setups": 0, "rejected_6r": 0, "news_filtered": 0})
                continue

            result = run_single_set(symbol, set_name, htf, mtf, ltf)
            all_results.append(result)
            print(f"  Trades: {result['total_trades']}, Balance: ${result['final_balance']:.2f}, Rejected6R: {result['rejected_6r']}")

    # Save results
    ledger_path = os.path.join(output_dir, "trade_ledger.csv")
    with open(ledger_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trade_id","symbol","set","direction","entry_ts","entry_price","fill_entry",
                     "size","entry_fee","initial_sl","tp1","tp2","tp3","planned_rr",
                     "exit_ts","exit_price","fill_exit","exit_reason","exit_fee","net_pnl","trailing_phase"])
        for r in all_results:
            for t in r["trades"]:
                w.writerow([t["trade_id"],t["symbol"],t["set"],t["direction"],t["entry_ts"],
                           t["entry_price"],t["fill_entry"],t["size"],t["entry_fee"],
                           t["initial_sl"],t["tp1"],t["tp2"],t["tp3"],t["planned_rr"],
                           t["exit_ts"],t["exit_price"],t["fill_exit"],t["exit_reason"],
                           t["exit_fee"],t["net_pnl"],t["trailing_phase"]])

    summary_path = os.path.join(output_dir, "summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset","set","total_trades","final_balance","net_pnl","rejected_6r","news_filtered","valid_setups"])
        for r in all_results:
            w.writerow([r["symbol"],r["set"],r["total_trades"],r["final_balance"],
                        r["final_balance"]-r["starting_balance"],r["rejected_6r"],
                        r["news_filtered"],r["valid_setups"]])

    json_path = os.path.join(output_dir, "full_results.json")
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}")
    return all_results


if __name__ == "__main__":
    main()
