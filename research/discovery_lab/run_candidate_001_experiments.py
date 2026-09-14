"""
PROJECT TOP1 — Candidate #001 Experiment Runner (Development 2021-2022).

Executes:
1. Baseline Candidate #001 Control (6.0R floor, 3x Stoch state machine)
2. EXP-001A-GEOM (3.0R floor, 3x Stoch state machine)
3. EXP-001B-STOCH (Decoupled: HTF Supertrend trend, MTF Stoch pullback, LTF Stoch trigger, 3.0R floor)

Strictly evaluates on Development research horizon (2021-2022).
"""

import os
import sys
import json
import csv
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle, SwingType
from market_data.data_manager import DataManager
from strategy_candidate_v2.run_backtest import compute_all_indicators, StateMachine, SwingCache
from strategy_engine.news.news_provider import NullNewsProvider
from backtesting.friction_model import FrictionModel
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, ASSETS, load_candles
from research.analytics.r_accounting import RAccountingEngine
from research.discovery_lab.oos_manager import OOSManager


def run_experiment_instance(
    symbol: str,
    set_name: str,
    htf_candles: List[Candle],
    mtf_candles: List[Candle],
    ltf_candles: List[Candle],
    min_rr_floor: float = 6.0,
    decoupled_stoch: bool = False,
    start_ts: int = OOSManager.DEV_START_TS,
    end_ts: int = OOSManager.DEV_END_TS,
) -> Dict[str, Any]:
    """
    Executes backtest with parameterized geometry and stochastic logic,
    filtering resulting trades strictly to [start_ts, end_ts].
    """
    starting_balance = 10000.0
    balance = starting_balance
    risk_pct = 0.01
    friction = FrictionModel()

    if len(htf_candles) < 50 or len(mtf_candles) < 50 or len(ltf_candles) < 50:
        empty_m = RAccountingEngine.compute_stream_metrics([])
        return {
            "symbol": symbol, "set": set_name, "total_trades_all_time": 0,
            "total_trades_dev": 0, "dev_trades": [], "metrics": empty_m,
            "rejected_rr": 0,
        }

    # Compute indicators
    htf = compute_all_indicators(htf_candles)
    mtf = compute_all_indicators(mtf_candles)
    ltf = compute_all_indicators(ltf_candles)

    htf_close_ts = htf["ts"] + htf["interval"]
    mtf_close_ts = mtf["ts"] + mtf["interval"]

    htf_sm = {1: StateMachine(), -1: StateMachine()}
    mtf_sm = {1: StateMachine(), -1: StateMachine()}
    ltf_sm = {1: StateMachine(), -1: StateMachine()}

    STOCH_HIGH = 75.0
    STOCH_LOW = 25.0

    def update_custom_state(sm: StateMachine, st_dir: int, k: float, d: float,
                            prev_k: float, prev_d: float, direction: int,
                            is_ltf: bool, is_htf: bool, swing_cache: SwingCache, candle_idx: int):
        if direction == 1:  # BULLISH
            if st_dir != 1:
                sm.state = 'IDLE'
                sm.peak_reached = False
                sm.pullback_reached = False
                return

            if decoupled_stoch and is_htf:
                sm.state = 'READY'
                sm.condition_met_ts = candle_idx
                sm.target_price = swing_cache.get_target(candle_idx, direction)
                return

            if sm.state == 'IDLE':
                if k >= STOCH_HIGH:
                    sm.state = 'WAITING_PEAK'
                    sm.peak_reached = True
                elif decoupled_stoch and not is_ltf:
                    if k <= STOCH_LOW:
                        sm.state = 'READY'
                        sm.condition_met_ts = candle_idx
                        sm.target_price = swing_cache.get_target(candle_idx, direction)
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
                if k >= STOCH_HIGH and not (decoupled_stoch and is_htf):
                    sm.state = 'WAITING_PEAK'
        else:  # BEARISH
            if st_dir != -1:
                sm.state = 'IDLE'
                sm.peak_reached = False
                sm.pullback_reached = False
                return

            if decoupled_stoch and is_htf:
                sm.state = 'READY'
                sm.condition_met_ts = candle_idx
                sm.target_price = swing_cache.get_target(candle_idx, direction)
                return

            if sm.state == 'IDLE':
                if k <= STOCH_LOW:
                    sm.state = 'WAITING_PEAK'
                    sm.peak_reached = True
                elif decoupled_stoch and not is_ltf:
                    if k >= STOCH_HIGH:
                        sm.state = 'READY'
                        sm.condition_met_ts = candle_idx
                        sm.target_price = swing_cache.get_target(candle_idx, direction)
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
                if k <= STOCH_LOW and not (decoupled_stoch and is_htf):
                    sm.state = 'WAITING_PEAK'

    trades = []
    active_pos = None
    trade_counter = 0
    rejected_rr = 0

    num_ltf = len(ltf_candles)
    ltf_high = ltf["high"]
    ltf_low = ltf["low"]
    ltf_close = ltf["close"]
    ltf_ts = ltf["ts"]

    last_htf_idx = -1
    last_mtf_idx = -1

    for i in range(10, num_ltf):
        if balance <= 0:
            break

        ltf_close_time = ltf_ts[i] + ltf["interval"]

        # Sync HTF
        h_idx = np.searchsorted(htf_close_ts, ltf_close_time, side='right') - 1
        if h_idx != last_htf_idx and 0 <= h_idx < len(htf_candles):
            last_htf_idx = h_idx
            for d in (1, -1):
                pk = htf["k"][h_idx - 1] if h_idx > 0 else htf["k"][h_idx]
                pd = htf["d"][h_idx - 1] if h_idx > 0 else htf["d"][h_idx]
                update_custom_state(htf_sm[d], htf["st_dir"][h_idx], htf["k"][h_idx], htf["d"][h_idx],
                                    pk, pd, d, is_ltf=False, is_htf=True, swing_cache=htf["swing_cache"], candle_idx=h_idx)

        # Sync MTF
        m_idx = np.searchsorted(mtf_close_ts, ltf_close_time, side='right') - 1
        if m_idx != last_mtf_idx and 0 <= m_idx < len(mtf_candles):
            last_mtf_idx = m_idx
            for d in (1, -1):
                pk = mtf["k"][m_idx - 1] if m_idx > 0 else mtf["k"][m_idx]
                pd = mtf["d"][m_idx - 1] if m_idx > 0 else mtf["d"][m_idx]
                update_custom_state(mtf_sm[d], mtf["st_dir"][m_idx], mtf["k"][m_idx], mtf["d"][m_idx],
                                    pk, pd, d, is_ltf=False, is_htf=False, swing_cache=mtf["swing_cache"], candle_idx=m_idx)

        # Update LTF
        for d in (1, -1):
            pk = ltf["k"][i - 1]
            pd = ltf["d"][i - 1]
            update_custom_state(ltf_sm[d], ltf["st_dir"][i], ltf["k"][i], ltf["d"][i],
                                pk, pd, d, is_ltf=True, is_htf=False, swing_cache=ltf["swing_cache"], candle_idx=i)

        # Manage active position
        if active_pos is not None:
            c_high = ltf_high[i]
            c_low = ltf_low[i]
            d = active_pos["direction"]

            if d == 1:
                active_pos["mfe_price"] = max(active_pos["mfe_price"], c_high)
                active_pos["mae_price"] = min(active_pos["mae_price"], c_low)
            else:
                active_pos["mfe_price"] = min(active_pos["mfe_price"], c_low)
                active_pos["mae_price"] = max(active_pos["mae_price"], c_high)

            exit_price = None
            exit_reason = None

            if d == 1:  # Long
                hit_sl = c_low <= active_pos["sl"]
                hit_tp1 = active_pos["phase"] == 1 and c_high >= active_pos["tp1"]
                hit_tp2 = active_pos["phase"] == 2 and c_high >= active_pos["tp2"]
                hit_tp3 = active_pos["phase"] == 3 and c_high >= active_pos["tp3"]

                if hit_sl and (hit_tp1 or hit_tp2 or hit_tp3):
                    exit_price = active_pos["sl"]
                    exit_reason = f"SL_COLLISION_PHASE_{active_pos['phase']}"
                elif hit_sl:
                    exit_price = active_pos["sl"]
                    exit_reason = f"STOP_LOSS_PHASE_{active_pos['phase']}"
                elif hit_tp1:
                    active_pos["phase"] = 2
                    active_pos["sl"] = active_pos["entry_price"]
                elif hit_tp2:
                    active_pos["phase"] = 3
                    active_pos["sl"] = active_pos["tp1"]
                elif hit_tp3:
                    exit_price = active_pos["tp3"]
                    exit_reason = "TAKE_PROFIT_3"
            else:  # Short
                hit_sl = c_high >= active_pos["sl"]
                hit_tp1 = active_pos["phase"] == 1 and c_low <= active_pos["tp1"]
                hit_tp2 = active_pos["phase"] == 2 and c_low <= active_pos["tp2"]
                hit_tp3 = active_pos["phase"] == 3 and c_low <= active_pos["tp3"]

                if hit_sl and (hit_tp1 or hit_tp2 or hit_tp3):
                    exit_price = active_pos["sl"]
                    exit_reason = f"SL_COLLISION_PHASE_{active_pos['phase']}"
                elif hit_sl:
                    exit_price = active_pos["sl"]
                    exit_reason = f"STOP_LOSS_PHASE_{active_pos['phase']}"
                elif hit_tp1:
                    active_pos["phase"] = 2
                    active_pos["sl"] = active_pos["entry_price"]
                elif hit_tp2:
                    active_pos["phase"] = 3
                    active_pos["sl"] = active_pos["tp1"]
                elif hit_tp3:
                    exit_price = active_pos["tp3"]
                    exit_reason = "TAKE_PROFIT_3"

            if exit_price is not None:
                pos = active_pos
                if d == 1:
                    fill_exit = friction.calculate_sell_fill(exit_price)
                    raw_pnl = (fill_exit - pos["fill_entry"]) * pos["size"]
                else:
                    fill_exit = friction.calculate_buy_fill(exit_price)
                    raw_pnl = (pos["fill_entry"] - fill_exit) * pos["size"]

                exit_fee = friction.calculate_fee(fill_exit * pos["size"])
                net_pnl = raw_pnl - pos["entry_fee"] - exit_fee
                balance += net_pnl

                realized_r = RAccountingEngine.calculate_trade_r(net_pnl, pos["entry_equity"], risk_pct)
                mfe_r, mae_r = RAccountingEngine.calculate_excursions(
                    d, pos["entry_price"], pos["initial_sl"], pos["mfe_price"], pos["mae_price"]
                )

                trades.append({
                    "trade_id": pos["id"],
                    "symbol": symbol,
                    "set": set_name,
                    "direction": d,
                    "entry_ts": pos["entry_ts"],
                    "entry_equity": pos["entry_equity"],
                    "entry_price": pos["entry_price"],
                    "fill_entry": pos["fill_entry"],
                    "size": pos["size"],
                    "entry_fee": pos["entry_fee"],
                    "initial_sl": pos["initial_sl"],
                    "tp1": pos["tp1"],
                    "tp2": pos["tp2"],
                    "tp3": pos["tp3"],
                    "planned_r": pos["planned_r"],
                    "exit_ts": ltf_close_time,
                    "exit_price": exit_price,
                    "fill_exit": fill_exit,
                    "exit_reason": exit_reason,
                    "exit_fee": exit_fee,
                    "net_pnl": net_pnl,
                    "realized_r": realized_r,
                    "mfe_r": mfe_r,
                    "mae_r": mae_r,
                    "trailing_phase": pos["phase"],
                })
                active_pos = None

        # Check entries
        if active_pos is None:
            for direction in (1, -1):
                if (htf_sm[direction].state == 'READY' and
                    mtf_sm[direction].state == 'READY' and
                    ltf_sm[direction].state == 'READY'):

                    ldv = float(ltf["st_val"][i])
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

                    reward = (tp3 - entry_price) if direction == 1 else (entry_price - tp3)
                    if reward <= 0:
                        rejected_rr += 1
                        htf_sm[direction].state = 'IDLE'
                        mtf_sm[direction].state = 'IDLE'
                        ltf_sm[direction].state = 'IDLE'
                        continue

                    rr = reward / risk
                    if rr < min_rr_floor:
                        rejected_rr += 1
                        htf_sm[direction].state = 'IDLE'
                        mtf_sm[direction].state = 'IDLE'
                        ltf_sm[direction].state = 'IDLE'
                        continue

                    # Enter position
                    trade_counter += 1
                    if direction == 1:
                        fill_entry = friction.calculate_buy_fill(entry_price)
                        fill_sl_exit = friction.calculate_sell_fill(sl_price)
                        unit_loss = (fill_entry - fill_sl_exit) + friction.calculate_fee(fill_entry) + friction.calculate_fee(fill_sl_exit)
                    else:
                        fill_entry = friction.calculate_sell_fill(entry_price)
                        fill_sl_exit = friction.calculate_buy_fill(sl_price)
                        unit_loss = (fill_sl_exit - fill_entry) + friction.calculate_fee(fill_entry) + friction.calculate_fee(fill_sl_exit)

                    max_dollar_loss = balance * risk_pct
                    position_size = max_dollar_loss / unit_loss if unit_loss > 0 else 0.0
                    notional_entry = fill_entry * position_size
                    entry_fee = friction.calculate_fee(notional_entry)

                    active_pos = {
                        "id": f"{symbol}_{set_name}_{trade_counter}",
                        "direction": direction,
                        "entry_ts": ltf_close_time,
                        "entry_equity": balance,
                        "entry_price": entry_price,
                        "fill_entry": fill_entry,
                        "size": position_size,
                        "entry_fee": entry_fee,
                        "initial_sl": sl_price,
                        "sl": sl_price,
                        "tp1": tp1,
                        "tp2": tp2,
                        "tp3": tp3,
                        "planned_r": rr,
                        "mfe_price": entry_price,
                        "mae_price": entry_price,
                        "phase": 1,
                    }

                    htf_sm[direction].state = 'IDLE'
                    mtf_sm[direction].state = 'IDLE'
                    ltf_sm[direction].state = 'IDLE'
                    break

    # Strictly filter trades to Development window
    dev_trades = OOSManager.filter_trades_to_window(trades, start_ts, end_ts)
    metrics = RAccountingEngine.compute_stream_metrics(dev_trades)

    return {
        "symbol": symbol,
        "set": set_name,
        "total_trades_all_time": len(trades),
        "total_trades_dev": len(dev_trades),
        "dev_trades": dev_trades,
        "metrics": metrics,
        "rejected_rr": rejected_rr,
    }


def main():
    print("=" * 80)
    print("PROJECT TOP1 — CANDIDATE #001 CONTROL & EXPERIMENT RUNNER (DEV 2021-2022)")
    print("=" * 80)

    experiments = [
        {"id": "CANDIDATE_001_CONTROL", "floor": 6.0, "decoupled": False,
         "hypothesis": "Benchmark Candidate #001 (Supertrend + Stochastic 3x state machine, 6.0R floor)"},
        {"id": "EXP-001A-GEOM", "floor": 3.0, "decoupled": False,
         "hypothesis": "Rationalize target geometry from 6.0R to 3.0R to test opportunity frequency"},
        {"id": "EXP-001B-STOCH", "floor": 3.0, "decoupled": True,
         "hypothesis": "Decouple MTF Stochastic: HTF pure trend, MTF pullback, LTF cross, 3.0R floor"},
    ]

    target_sets = ["Set 1", "Set 2", "Set 3", "Set 4"]  # Set 5 and Set 6 have missing 2021-2022 data in cache

    all_exp_results = {}

    for exp in experiments:
        exp_id = exp["id"]
        print(f"\n>>> Running Experiment: {exp_id} ({exp['hypothesis']})")
        exp_results = []

        for symbol in ASSETS:
            for s_name in target_sets:
                sc = TIMEFRAME_SETS[s_name]
                htf = load_candles(symbol, sc["HTF"])
                mtf = load_candles(symbol, sc["MTF"])
                ltf = load_candles(symbol, sc["LTF"])

                if not htf or not mtf or not ltf:
                    print(f"  {symbol} {s_name}: MISSING DATA")
                    continue

                # Filter candles up to DEV_END_TS
                htf_dev = OOSManager.get_development_candles_by_date(htf, include_warmup=True)
                mtf_dev = OOSManager.get_development_candles_by_date(mtf, include_warmup=True)
                ltf_dev = OOSManager.get_development_candles_by_date(ltf, include_warmup=True)

                res = run_experiment_instance(
                    symbol, s_name, htf_dev, mtf_dev, ltf_dev,
                    min_rr_floor=exp["floor"],
                    decoupled_stoch=exp["decoupled"],
                )
                exp_results.append(res)
                m = res["metrics"]
                print(f"  {symbol} {s_name}: N={res['total_trades_dev']} | Net R={m['net_r']:+.2f}R | "
                      f"Exp={m['expectancy_r']:+.2f}R | MaxDD={m['max_drawdown_r']:.2f}R | "
                      f"Confidence={m['sample_confidence']}")

        all_exp_results[exp_id] = exp_results

    # Output executive milestone report
    print("\n" + "=" * 80)
    print("EXECUTIVE MILESTONE REPORTS (DEV 2021-2022)")
    print("=" * 80)

    for exp in experiments:
        exp_id = exp["id"]
        results = all_exp_results[exp_id]
        total_dev_n = sum(r["total_trades_dev"] for r in results)
        total_net_r = sum(r["metrics"]["net_r"] for r in results)
        sets_with_100_trades = [f"{r['symbol']} {r['set']}" for r in results if r["total_trades_dev"] >= 100]

        print(f"\nEXPERIMENT ID: {exp_id}")
        print(f"HYPOTHESIS: {exp['hypothesis']}")
        print(f"RULES: Floor={exp['floor']}R | Decoupled={exp['decoupled']}")
        print(f"DEV HORIZON: 2021-01-01 to 2022-12-31 UTC")
        print(f"TOTAL DEV TRADES: {total_dev_n} across {len(results)} set instances")
        print(f"TOTAL DEV NET R: {total_net_r:+.2f}R")
        print(f"SETS SATISFYING N >= 100: {len(sets_with_100_trades)} ({', '.join(sets_with_100_trades) if sets_with_100_trades else 'NONE'})")

        if len(sets_with_100_trades) == 0:
            print(f"VERDICT: FALSIFIED / INSUFFICIENT OPPORTUNITY (No set reached N >= 100 in Dev)")
            print(f"NEXT ACTION: Advance to systematic discovery across 8 strategy families")
        else:
            print(f"VERDICT: PROCEED TO MULTI-DIMENSIONAL ROBUSTNESS")
            print(f"NEXT ACTION: Run cost stress and parameter perturbation on qualified sets")

    # Save output to discovery lab results
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "results", "candidate_001_experiments_dev.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        summary = {
            exp_id: [
                {
                    "symbol": r["symbol"],
                    "set": r["set"],
                    "total_trades_dev": r["total_trades_dev"],
                    "metrics": r["metrics"],
                    "rejected_rr": r["rejected_rr"],
                }
                for r in res_list
            ]
            for exp_id, res_list in all_exp_results.items()
        }
        json.dump(summary, f, indent=2)
    print(f"\nDetailed results saved to: {out_path}")


if __name__ == "__main__":
    main()
