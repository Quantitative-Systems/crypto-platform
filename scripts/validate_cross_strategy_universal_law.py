"""Validate the Universal 3-Pillar Meta-Framework Across Multiple Strategy Dialects.

Tests whether multiple strategy definitions:
- Family A: SMC Order Blocks (F05)
- Family B: ICT Fair Value Gaps (F06)
- Family C: Liquidity Sweeps / Pools (F04)
- Family D: Classical Support & Resistance / Structure (F01/F02)
- Family E: Fibonacci Golden Zones (F09)

all generate positive asymmetric alpha when plugged into the SAME universal engine:
HTF Bias -> MTF KeyZone Setup -> LTF Entry -> LTF SL (ATR protected) -> MTF Trailing -> HTF TP.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.contracts import StructuralBreakType
from market_model.state_generator import MarketStateGenerator
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator, MacroPhaseBaton
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

ALL_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "NEARUSDT"]

def evaluate_multi_family_framework():
    coordinator = CascadingFractalCoordinator(min_target_r=4.0)
    engine = CausalBacktestEngine(taker_fee_bps=2.0, slippage_bps=1.0, min_target_r=4.0, max_holding_bars=200)

    # We will test 4 distinct KeyZone / Setup definitions across Set 2 (1w -> 1d -> 4h) and Set 3 (1d -> 4h -> 1h)
    strategies = [
        {"id": "SMC_ORDER_BLOCKS", "desc": "SMC Unmitigated Order Blocks (F05)"},
        {"id": "ICT_FAIR_VALUE_GAPS", "desc": "ICT Fair Value Gaps / Imbalances (F06)"},
        {"id": "LIQUIDITY_SWEEPS", "desc": "ICT/Price Action Liquidity Pool Sweeps (F04)"},
        {"id": "PURE_STRUCTURE_SWINGS", "desc": "Dow / Classical Price Action Key Swings (F01/F02)"},
    ]

    results = {}

    for strat in strategies:
        strat_id = strat["id"]
        total_trades = 0
        total_wins = 0
        total_r = 0.0
        gross_win = 0.0
        gross_loss = 0.0

        for symbol in ALL_ASSETS:
            all_data = {}
            for tf in ["1M", "1w", "1d", "4h", "1h"]:
                arrs = load_series_arrays(symbol, tf)
                if arrs is not None:
                    all_data[tf] = arrs

            # Test on Set 2 (1w -> 1d -> 4h)
            for target_set in ["SET_2", "SET_3"]:
                cfg = coordinator.TIMEFRAME_SETS[target_set]
                htf_tf = cfg["htf"]
                mtf_tf = cfg["mtf"]
                ltf_tf = cfg["ltf"]

                if htf_tf not in all_data or mtf_tf not in all_data or ltf_tf not in all_data:
                    continue

                htf_data = all_data[htf_tf]
                mtf_data = all_data[mtf_tf]
                ltf_data = all_data[ltf_tf]

                ltf_closes = ltf_data["c"]
                ltf_ts = ltf_data["ts"]
                htf_close_ts = htf_data["close_ts"]
                mtf_close_ts = mtf_data["close_ts"]

                candidates = []
                trailing_map = {}

                last_htf_idx = -1
                last_htf_state = None
                last_mtf_idx = -1
                last_mtf_state = None

                risk_budget = 1000.0 * 0.01

                for i in range(25, len(ltf_closes)):
                    t_curr = int(ltf_ts[i])
                    curr_px = float(ltf_closes[i])

                    # 1. HTF Macro Baton / Phase
                    baton, demand_tgt, supply_tgt = coordinator.evaluate_macro_baton(symbol, t_curr, all_data)
                    if baton in (MacroPhaseBaton.BULLISH_EXPANSION, MacroPhaseBaton.BULLISH_PULLBACK):
                        auth_dir = 1
                    elif baton in (MacroPhaseBaton.BEARISH_EXPANSION, MacroPhaseBaton.BEARISH_PULLBACK):
                        auth_dir = -1
                    else:
                        continue

                    # MTF State
                    idx_mtf = np.searchsorted(mtf_close_ts, t_curr, side="right") - 1
                    if idx_mtf < 15:
                        continue
                    if idx_mtf != last_mtf_idx:
                        sm = max(0, idx_mtf - 200)
                        last_mtf_state = coordinator.generators[mtf_tf].generate(
                            symbol=symbol,
                            opens=mtf_data["o"][sm : idx_mtf + 1],
                            highs=mtf_data["h"][sm : idx_mtf + 1],
                            lows=mtf_data["l"][sm : idx_mtf + 1],
                            closes=mtf_data["c"][sm : idx_mtf + 1],
                            volumes=mtf_data["v"][sm : idx_mtf + 1],
                            timestamps=mtf_data["ts"][sm : idx_mtf + 1],
                        )
                        last_mtf_idx = idx_mtf

                    mtf_state = last_mtf_state
                    if mtf_state is None:
                        continue

                    # 2. MTF Setup / KeyZone check based on the strategy dialect
                    setup_valid = False
                    if strat_id == "SMC_ORDER_BLOCKS":
                        obs = mtf_state.zones.order_blocks
                        if auth_dir == 1:
                            setup_valid = any(ob.is_bullish and not ob.is_mitigated for ob in obs)
                        else:
                            setup_valid = any(not ob.is_bullish and not ob.is_mitigated for ob in obs)

                    elif strat_id == "ICT_FAIR_VALUE_GAPS":
                        fvgs = mtf_state.zones.fair_value_gaps
                        if auth_dir == 1:
                            setup_valid = any(fvg.is_bullish for fvg in fvgs)
                        else:
                            setup_valid = any(not fvg.is_bullish for fvg in fvgs)

                    elif strat_id == "LIQUIDITY_SWEEPS":
                        # Liquidity pool presence
                        pools = mtf_state.liquidity.equal_highs if auth_dir == -1 else mtf_state.liquidity.equal_lows
                        setup_valid = len(pools) > 0 or (auth_dir == 1 and mtf_state.zones.premium_discount_zone == "DISCOUNT") or (auth_dir == -1 and mtf_state.zones.premium_discount_zone == "PREMIUM")

                    elif strat_id == "PURE_STRUCTURE_SWINGS":
                        # Pure Dow / Structure discount/premium swing alignment
                        pd = mtf_state.zones.premium_discount_zone
                        setup_valid = (auth_dir == 1 and pd == "DISCOUNT") or (auth_dir == -1 and pd == "PREMIUM")

                    if not setup_valid:
                        continue

                    # MTF Trailing Map
                    if auth_dir == 1:
                        tc = []
                        if mtf_state.structure.last_major_low and mtf_state.structure.last_major_low.price < curr_px:
                            tc.append(mtf_state.structure.last_major_low.price)
                        if mtf_state.structure.last_minor_low and mtf_state.structure.last_minor_low.price < curr_px:
                            tc.append(mtf_state.structure.last_minor_low.price)
                        if tc:
                            trailing_map[t_curr] = max(tc)
                    else:
                        tc = []
                        if mtf_state.structure.last_major_high and mtf_state.structure.last_major_high.price > curr_px:
                            tc.append(mtf_state.structure.last_major_high.price)
                        if mtf_state.structure.last_minor_high and mtf_state.structure.last_minor_high.price > curr_px:
                            tc.append(mtf_state.structure.last_minor_high.price)
                        if tc:
                            trailing_map[t_curr] = min(tc)

                    # 3. LTF Entry (Precision Break)
                    sl_start = max(0, i - 40)
                    ltf_st = coordinator.generators[ltf_tf].generate(
                        symbol=symbol,
                        opens=ltf_data["o"][sl_start : i + 1],
                        highs=ltf_data["h"][sl_start : i + 1],
                        lows=ltf_data["l"][sl_start : i + 1],
                        closes=ltf_data["c"][sl_start : i + 1],
                        volumes=ltf_data["v"][sl_start : i + 1],
                        timestamps=ltf_data["ts"][sl_start : i + 1],
                    )

                    breaks = ltf_st.structure.recent_breaks
                    if not breaks:
                        continue
                    b = breaks[-1]
                    b_dir = 1 if b.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH) else (-1 if b.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH) else 0)
                    if b_dir != auth_dir:
                        continue

                    # 4. LTF SL + Volatility Floor
                    min_dist = max(ltf_st.measurements.atr * 1.5, curr_px * 0.005)
                    if b_dir == 1:
                        sl_ref = ltf_st.structure.last_minor_low or ltf_st.structure.last_major_low
                        struct_sl = sl_ref.price * 0.999 if (sl_ref and sl_ref.price < curr_px) else (curr_px - min_dist)
                        init_sl = min(struct_sl, curr_px - min_dist)
                        risk_d = curr_px - init_sl
                        tgt_px = supply_tgt if (supply_tgt and supply_tgt > curr_px) else (curr_px + 4.5 * risk_d)
                    else:
                        sl_ref = ltf_st.structure.last_minor_high or ltf_st.structure.last_major_high
                        struct_sl = sl_ref.price * 1.001 if (sl_ref and sl_ref.price > curr_px) else (curr_px + min_dist)
                        init_sl = max(struct_sl, curr_px + min_dist)
                        risk_d = init_sl - curr_px
                        tgt_px = demand_tgt if (demand_tgt and demand_tgt < curr_px) else (curr_px - 4.5 * risk_d)

                    if risk_d <= 0 or abs(tgt_px - curr_px) / risk_d < 4.0:
                        continue

                    pos_sz = risk_budget / (risk_d / curr_px)
                    candidates.append({
                        "bar_index": i,
                        "timestamp_ms": t_curr,
                        "symbol": symbol,
                        "origin_set": target_set,
                        "direction": b_dir,
                        "entry_price": curr_px,
                        "stop_price": init_sl,
                        "target_price": tgt_px,
                        "target_r": abs(tgt_px - curr_px) / risk_d,
                        "macro_baton": baton.value,
                        "risk_dist": risk_d,
                        "reward_dist": abs(tgt_px - curr_px),
                        "position_size_usd": pos_sz,
                        "meta": {"target_set": target_set},
                    })

                if not candidates:
                    continue

                res = engine.execute_stream(
                    stream_id=f"{strat_id}_{symbol}_{target_set}",
                    symbol=symbol,
                    timeframe_set=target_set,
                    hypothesis="UNIVERSAL_3_PILLARS",
                    ltf_opens=ltf_data["o"],
                    ltf_highs=ltf_data["h"],
                    ltf_lows=ltf_data["l"],
                    ltf_closes=ltf_data["c"],
                    ltf_timestamps=ltf_data["ts"],
                    signal_candidates=candidates,
                    mtf_trailing_levels=trailing_map,
                )

                total_trades += res.total_trades
                total_wins += res.win_count
                total_r += res.total_r
                gross_win += sum(t.realized_r for t in res.trades if t.realized_r > 0)
                gross_loss += abs(sum(t.realized_r for t in res.trades if t.realized_r <= 0))

        wr = total_wins / max(total_trades, 1) * 100
        pf = gross_win / max(gross_loss, 0.001)
        results[strat_id] = {
            "desc": strat["desc"],
            "trades": total_trades,
            "win_rate": round(wr, 1),
            "net_r": round(total_r, 2),
            "profit_factor": round(pf, 2),
        }

    print("=" * 90)
    print("EMPIRICAL TEST OF THE 3-PILLAR META-FRAMEWORK ACROSS MULTIPLE STRATEGY DIALECTS")
    print("=" * 90)
    for sid, r in results.items():
        print(f"[{sid:<22}] | Trades: {r['trades']:>4} | WR: {r['win_rate']:>5.1f}% | Net R: {r['net_r']:>+8.2f}R | PF: {r['profit_factor']:>5.2f} | {r['desc']}")
    print("=" * 90)

if __name__ == "__main__":
    evaluate_multi_family_framework()
