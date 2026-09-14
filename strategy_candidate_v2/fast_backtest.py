"""
Ultra-fast backtest using numpy throughout.
Avoids swing detection bottleneck by using rolling window high/low for targets.
"""

import os
import sys
import csv
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from bisect import bisect_right

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.fast_indicators import compute_indicators_fast
from backtesting.friction_model import FrictionModel
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, ASSETS, load_candles


def rolling_target_high(highs: np.ndarray, window: int = 20) -> np.ndarray:
    """Causal rolling max of highs: result[i] = max(highs[i-window:i])."""
    n = len(highs)
    result = np.full(n, np.nan)
    if n <= window:
        return result
    try:
        from numpy.lib.stride_tricks import sliding_window_view
        w = sliding_window_view(highs[:-1], window_shape=window)
        result[window:n] = np.max(w[:n - window], axis=1)
    except Exception:
        for i in range(window, n):
            result[i] = np.max(highs[i - window:i])
    return result


def rolling_target_low(lows: np.ndarray, window: int = 20) -> np.ndarray:
    """Causal rolling min of lows: result[i] = min(lows[i-window:i])."""
    n = len(lows)
    result = np.full(n, np.nan)
    if n <= window:
        return result
    try:
        from numpy.lib.stride_tricks import sliding_window_view
        w = sliding_window_view(lows[:-1], window_shape=window)
        result[window:n] = np.min(w[:n - window], axis=1)
    except Exception:
        for i in range(window, n):
            result[i] = np.min(lows[i - window:i])
    return result


def run_single_set(symbol: str, set_name: str, htf_c: List[Candle],
                   mtf_c: List[Candle], ltf_c: List[Candle]) -> Dict[str, Any]:
    """Run backtest for a single asset x set."""
    starting_balance = 10000.0
    risk_pct = 0.01
    friction = FrictionModel()

    if len(htf_c) < 50 or len(mtf_c) < 50 or len(ltf_c) < 50:
        return {"symbol": symbol, "set": set_name, "starting_balance": starting_balance,
                "final_balance": starting_balance, "trades": [], "total_trades": 0,
                "valid_setups": 0, "rejected_6r": 0, "news_filtered": 0}

    # Compute indicators
    htf = compute_indicators_fast(htf_c)
    mtf = compute_indicators_fast(mtf_c)
    ltf = compute_indicators_fast(ltf_c)

    htf_close_ts = htf["ts"] + htf["interval"]
    mtf_close_ts = mtf["ts"] + mtf["interval"]

    # Pre-compute targets (rolling high/low as proxy for swing targets)
    htf_target_high = rolling_target_high(htf["high"], 20)
    htf_target_low = rolling_target_low(htf["low"], 20)
    mtf_target_high = rolling_target_high(mtf["high"], 20)
    mtf_target_low = rolling_target_low(mtf["low"], 20)
    ltf_target_high = rolling_target_high(ltf["high"], 20)
    ltf_target_low = rolling_target_low(ltf["low"], 20)

    # State machines using simple dicts for speed
    # States: 0=IDLE, 1=WAITING_PEAK, 2=WAITING_PULLBACK, 3=WAITING_CROSSOVER, 4=READY
    htf_state = {1: 0, -1: 0}
    mtf_state = {1: 0, -1: 0}
    ltf_state = {1: 0, -1: 0}
    htf_target = {1: None, -1: None}
    mtf_target = {1: None, -1: None}
    ltf_target = {1: None, -1: None}

    balance = starting_balance
    trades = []
    active_pos = None
    trade_counter = 0
    rejected_6r = 0
    news_filtered = 0
    valid_setups = 0

    num_ltf = len(ltf_c)
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
            # Trailing
            if direction == 1:
                if active_pos["phase"] == 1:
                    if ldv > active_pos["sl"]: active_pos["sl"] = ldv
                    if mdv >= active_pos["tp1"]: active_pos["phase"] = 2
                elif active_pos["phase"] == 2:
                    if mdv >= active_pos["sl"]: active_pos["sl"] = mdv; active_pos["phase"] = 3
                elif active_pos["phase"] == 3:
                    if mdv > active_pos["sl"]: active_pos["sl"] = mdv
                    if hdv >= active_pos["sl"]: active_pos["sl"] = hdv; active_pos["phase"] = 4
                elif active_pos["phase"] == 4:
                    if hdv > active_pos["sl"]: active_pos["sl"] = hdv

                if ltf_low[i] <= active_pos["sl"]:
                    fill_exit = friction.calculate_sell_fill(active_pos["sl"])
                    pnl = (fill_exit - active_pos["fill_entry"]) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({"trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "LONG", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["sl"], "fill_exit": fill_exit,
                        "exit_reason": "SL", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"]})
                    balance += net_pnl; active_pos = None
                elif ltf_high[i] >= active_pos["tp3"]:
                    fill_exit = friction.calculate_sell_fill(active_pos["tp3"])
                    pnl = (fill_exit - active_pos["fill_entry"]) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({"trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "LONG", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["tp3"], "fill_exit": fill_exit,
                        "exit_reason": "TP3", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"]})
                    balance += net_pnl; active_pos = None
            else:  # SHORT
                if active_pos["phase"] == 1:
                    if ldv < active_pos["sl"]: active_pos["sl"] = ldv
                    if mdv <= active_pos["tp1"]: active_pos["phase"] = 2
                elif active_pos["phase"] == 2:
                    if mdv <= active_pos["sl"]: active_pos["sl"] = mdv; active_pos["phase"] = 3
                elif active_pos["phase"] == 3:
                    if mdv < active_pos["sl"]: active_pos["sl"] = mdv
                    if hdv <= active_pos["sl"]: active_pos["sl"] = hdv; active_pos["phase"] = 4
                elif active_pos["phase"] == 4:
                    if hdv < active_pos["sl"]: active_pos["sl"] = hdv

                if ltf_high[i] >= active_pos["sl"]:
                    fill_exit = friction.calculate_buy_fill(active_pos["sl"])
                    pnl = (active_pos["fill_entry"] - fill_exit) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({"trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "SHORT", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["sl"], "fill_exit": fill_exit,
                        "exit_reason": "SL", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"]})
                    balance += net_pnl; active_pos = None
                elif ltf_low[i] <= active_pos["tp3"]:
                    fill_exit = friction.calculate_buy_fill(active_pos["tp3"])
                    pnl = (active_pos["fill_entry"] - fill_exit) * active_pos["size"]
                    exit_fee = friction.calculate_fee(fill_exit * active_pos["size"])
                    net_pnl = pnl - active_pos["entry_fee"] - exit_fee
                    trades.append({"trade_id": active_pos["id"], "symbol": symbol, "set": set_name,
                        "direction": "SHORT", "entry_ts": active_pos["entry_ts"],
                        "entry_price": active_pos["entry_price"], "fill_entry": active_pos["fill_entry"],
                        "size": active_pos["size"], "entry_fee": active_pos["entry_fee"],
                        "initial_sl": active_pos["initial_sl"], "tp1": active_pos["tp1"],
                        "tp2": active_pos["tp2"], "tp3": active_pos["tp3"],
                        "planned_rr": active_pos["planned_rr"], "exit_ts": ltf_close_time,
                        "exit_price": active_pos["tp3"], "fill_exit": fill_exit,
                        "exit_reason": "TP3", "exit_fee": exit_fee, "net_pnl": net_pnl,
                        "trailing_phase": active_pos["phase"]})
                    balance += net_pnl; active_pos = None
            continue

        # Update state machines
        for direction in [1, -1]:
            # HTF
            s = htf_state[direction]
            if direction == 1:
                if hdi != 1:
                    htf_state[direction] = 0
                elif s == 0:
                    if hk >= 75.0: htf_state[direction] = 1
                elif s == 1:
                    if hk <= 25.0: htf_state[direction] = 2
                elif s == 2:
                    if hdi == 1:
                        htf_state[direction] = 4
                        htf_target[direction] = float(htf_target_high[htf_idx]) if not np.isnan(htf_target_high[htf_idx]) else None
                    else:
                        htf_state[direction] = 0
            else:
                if hdi != -1:
                    htf_state[direction] = 0
                elif s == 0:
                    if hk <= 25.0: htf_state[direction] = 1
                elif s == 1:
                    if hk >= 75.0: htf_state[direction] = 2
                elif s == 2:
                    if hdi == -1:
                        htf_state[direction] = 4
                        htf_target[direction] = float(htf_target_low[htf_idx]) if not np.isnan(htf_target_low[htf_idx]) else None
                    else:
                        htf_state[direction] = 0

            # MTF
            s = mtf_state[direction]
            if direction == 1:
                if mdi != 1:
                    mtf_state[direction] = 0
                elif s == 0:
                    if mk >= 75.0: mtf_state[direction] = 1
                elif s == 1:
                    if mk <= 25.0: mtf_state[direction] = 2
                elif s == 2:
                    if mdi == 1:
                        mtf_state[direction] = 4
                        mtf_target[direction] = float(mtf_target_high[mtf_idx]) if not np.isnan(mtf_target_high[mtf_idx]) else None
                    else:
                        mtf_state[direction] = 0
            else:
                if mdi != -1:
                    mtf_state[direction] = 0
                elif s == 0:
                    if mk <= 25.0: mtf_state[direction] = 1
                elif s == 1:
                    if mk >= 75.0: mtf_state[direction] = 2
                elif s == 2:
                    if mdi == -1:
                        mtf_state[direction] = 4
                        mtf_target[direction] = float(mtf_target_low[mtf_idx]) if not np.isnan(mtf_target_low[mtf_idx]) else None
                    else:
                        mtf_state[direction] = 0

            # LTF
            s = ltf_state[direction]
            if direction == 1:
                if ldi != 1:
                    ltf_state[direction] = 0
                elif s == 0:
                    if lk >= 75.0: ltf_state[direction] = 1
                elif s == 1:
                    if lk <= 25.0: ltf_state[direction] = 2
                elif s == 2:
                    ltf_state[direction] = 3
                elif s == 3:
                    if plk <= pld and lk > ld:
                        if ldi == 1:
                            ltf_state[direction] = 4
                            ltf_target[direction] = float(ltf_target_high[i]) if not np.isnan(ltf_target_high[i]) else None
                        else:
                            ltf_state[direction] = 0
            else:
                if ldi != -1:
                    ltf_state[direction] = 0
                elif s == 0:
                    if lk <= 25.0: ltf_state[direction] = 1
                elif s == 1:
                    if lk >= 75.0: ltf_state[direction] = 2
                elif s == 2:
                    ltf_state[direction] = 3
                elif s == 3:
                    if plk >= pld and lk < ld:
                        if ldi == -1:
                            ltf_state[direction] = 4
                            ltf_target[direction] = float(ltf_target_low[i]) if not np.isnan(ltf_target_low[i]) else None
                        else:
                            ltf_state[direction] = 0

        # Check entry signals
        for direction in [1, -1]:
            if htf_state[direction] == 4 and mtf_state[direction] == 4 and ltf_state[direction] == 4:
                valid_setups += 1
                entry_price = float(ltf_close[i])
                sl_price = ldv
                tp3 = htf_target[direction]
                tp2 = mtf_target[direction]
                tp1 = ltf_target[direction]

                if tp3 is None or tp2 is None or tp1 is None:
                    htf_state[direction] = 0; mtf_state[direction] = 0; ltf_state[direction] = 0
                    continue

                risk = abs(entry_price - sl_price)
                if risk <= 0:
                    htf_state[direction] = 0; mtf_state[direction] = 0; ltf_state[direction] = 0
                    continue

                reward = abs(tp3 - entry_price)
                rr = reward / risk

                if rr < 6.0:
                    rejected_6r += 1
                    htf_state[direction] = 0; mtf_state[direction] = 0; ltf_state[direction] = 0
                    continue

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
                htf_state[direction] = 0; mtf_state[direction] = 0; ltf_state[direction] = 0
                break

    return {
        "symbol": symbol, "set": set_name, "starting_balance": starting_balance,
        "final_balance": balance, "trades": trades, "total_trades": len(trades),
        "valid_setups": valid_setups, "rejected_6r": rejected_6r, "news_filtered": news_filtered,
    }


def main():
    import time
    t0 = time.time()
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(output_dir, exist_ok=True)
    all_results = []

    # Optional: limit via env var for smoke test, e.g. SMOKE=1 runs 1 combo
    import os as _os
    smoke = _os.environ.get("SMOKE", "")
    combos = [(s, n) for s in ASSETS for n in TIMEFRAME_SETS]
    if smoke:
        combos = combos[:1]

    for symbol, set_name in combos:
        sc = TIMEFRAME_SETS[set_name]
        print(f"Running: {symbol} {set_name} ({sc['style']})", flush=True)
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
        print(f"  Trades: {result['total_trades']}, Balance: ${result['final_balance']:.2f}, Rejected6R: {result['rejected_6r']}", flush=True)

    # Save
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
