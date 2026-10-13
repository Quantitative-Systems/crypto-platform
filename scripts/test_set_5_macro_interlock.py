"""Test Set 5 with Macro Order Block Interlocking & Scaled Targets.

Hypothesis: A 3m trade cannot reach 4R+ in open air. But if the 3m structure shift
occurs INSIDE a 4H or 1D KeyZone (Order Block / Fair Value Gap), it is riding
an institutional inflection point, allowing for massive expansion.
"""
import sys
from pathlib import Path
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.contracts import StructuralBreakType
from market_model.state_generator import MarketStateGenerator
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator, MacroPhaseBaton
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

ALL_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "NEARUSDT", "DOTUSDT"]

def run_set_5_interlock_test(target_r_val: float = 3.0, require_4h_keyzone: bool = True):
    coordinator = CascadingFractalCoordinator(min_target_r=target_r_val)
    engine = CausalBacktestEngine(taker_fee_bps=2.0, slippage_bps=1.0, min_target_r=target_r_val, max_holding_bars=250)

    total_trades = 0
    total_wins = 0
    total_r = 0.0
    gross_win = 0.0
    gross_loss = 0.0

    print(f"\n--- Testing Set 5: Target={target_r_val}R | Require 4H KeyZone={require_4h_keyzone} ---", flush=True)

    for symbol in ALL_ASSETS:
        all_data = {}
        for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
            arrs = load_series_arrays(symbol, tf)
            if arrs is not None:
                all_data[tf] = arrs

        if "3m" not in all_data or "4h" not in all_data or "15m" not in all_data:
            continue

        ltf_data = all_data["3m"]
        mtf_data = all_data["15m"]
        h4_data = all_data["4h"]

        ltf_closes = ltf_data["c"]
        ltf_ts = ltf_data["ts"]
        h4_close_ts = h4_data["close_ts"]
        mtf_close_ts = mtf_data["close_ts"]

        candidates = []
        trailing_map = {}
        last_4h_idx = -1
        last_4h_state = None
        last_mtf_idx = -1
        last_mtf_state = None

        risk_budget = 1000.0 * 0.01

        for i in range(25, len(ltf_closes)):
            t_curr = int(ltf_ts[i])
            curr_px = float(ltf_closes[i])

            baton, demand_tgt, supply_tgt = coordinator.evaluate_macro_baton(symbol, t_curr, all_data)
            if baton in (MacroPhaseBaton.BULLISH_EXPANSION, MacroPhaseBaton.BULLISH_PULLBACK):
                auth_dir = 1
            elif baton in (MacroPhaseBaton.BEARISH_EXPANSION, MacroPhaseBaton.BEARISH_PULLBACK):
                auth_dir = -1
            else:
                continue

            # 4H KeyZone check
            if require_4h_keyzone:
                idx_4h = np.searchsorted(h4_close_ts, t_curr, side="right") - 1
                if idx_4h < 15:
                    continue
                if idx_4h != last_4h_idx:
                    s4 = max(0, idx_4h - 150)
                    last_4h_state = coordinator.generators["4h"].generate(
                        symbol=symbol,
                        opens=h4_data["o"][s4 : idx_4h + 1],
                        highs=h4_data["h"][s4 : idx_4h + 1],
                        lows=h4_data["l"][s4 : idx_4h + 1],
                        closes=h4_data["c"][s4 : idx_4h + 1],
                        volumes=h4_data["v"][s4 : idx_4h + 1],
                        timestamps=h4_data["ts"][s4 : idx_4h + 1],
                    )
                    last_4h_idx = idx_4h

                if last_4h_state is None:
                    continue

                has_4h_ob = len(last_4h_state.zones.order_blocks) > 0
                has_4h_fvg = len(last_4h_state.zones.fair_value_gaps) > 0
                pd_4h = last_4h_state.zones.premium_discount_zone

                if auth_dir == 1 and not (pd_4h == "DISCOUNT" and (has_4h_ob or has_4h_fvg)):
                    continue
                elif auth_dir == -1 and not (pd_4h == "PREMIUM" and (has_4h_ob or has_4h_fvg)):
                    continue

            # MTF 15m check
            idx_mtf = np.searchsorted(mtf_close_ts, t_curr, side="right") - 1
            if idx_mtf < 15:
                continue
            if idx_mtf != last_mtf_idx:
                sm = max(0, idx_mtf - 150)
                last_mtf_state = coordinator.generators["15m"].generate(
                    symbol=symbol,
                    opens=mtf_data["o"][sm : idx_mtf + 1],
                    highs=mtf_data["h"][sm : idx_mtf + 1],
                    lows=mtf_data["l"][sm : idx_mtf + 1],
                    closes=mtf_data["c"][sm : idx_mtf + 1],
                    volumes=mtf_data["v"][sm : idx_mtf + 1],
                    timestamps=mtf_data["ts"][sm : idx_mtf + 1],
                )
                last_mtf_idx = idx_mtf

            if last_mtf_state is None:
                continue

            # Trailing map
            if auth_dir == 1:
                tc = []
                if last_mtf_state.structure.last_major_low and last_mtf_state.structure.last_major_low.price < curr_px:
                    tc.append(last_mtf_state.structure.last_major_low.price)
                if last_mtf_state.structure.last_minor_low and last_mtf_state.structure.last_minor_low.price < curr_px:
                    tc.append(last_mtf_state.structure.last_minor_low.price)
                if tc:
                    trailing_map[t_curr] = max(tc)
            else:
                tc = []
                if last_mtf_state.structure.last_major_high and last_mtf_state.structure.last_major_high.price > curr_px:
                    tc.append(last_mtf_state.structure.last_major_high.price)
                if last_mtf_state.structure.last_minor_high and last_mtf_state.structure.last_minor_high.price > curr_px:
                    tc.append(last_mtf_state.structure.last_minor_high.price)
                if tc:
                    trailing_map[t_curr] = min(tc)

            # 3m State
            sl_start = max(0, i - 40)
            ltf_st = coordinator.generators["3m"].generate(
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

            # Volatility stop floor
            atr_fl = max(ltf_st.measurements.atr, curr_px * 0.005)
            min_dist = atr_fl * 1.5

            if b_dir == 1:
                sl_ref = ltf_st.structure.last_minor_low or ltf_st.structure.last_major_low
                struct_sl = sl_ref.price * 0.999 if (sl_ref and sl_ref.price < curr_px) else (curr_px - min_dist)
                init_sl = min(struct_sl, curr_px - min_dist)
                risk_d = curr_px - init_sl
                tgt_px = curr_px + target_r_val * risk_d
            else:
                sl_ref = ltf_st.structure.last_minor_high or ltf_st.structure.last_major_high
                struct_sl = sl_ref.price * 1.001 if (sl_ref and sl_ref.price > curr_px) else (curr_px + min_dist)
                init_sl = max(struct_sl, curr_px + min_dist)
                risk_d = init_sl - curr_px
                tgt_px = curr_px - target_r_val * risk_d

            if risk_d <= 0:
                continue

            pos_sz = risk_budget / (risk_d / curr_px)
            candidates.append({
                "bar_index": i,
                "timestamp_ms": t_curr,
                "symbol": symbol,
                "origin_set": "SET_5",
                "direction": b_dir,
                "entry_price": curr_px,
                "stop_price": init_sl,
                "target_price": tgt_px,
                "target_r": target_r_val,
                "macro_baton": baton.value,
                "risk_dist": risk_d,
                "reward_dist": abs(tgt_px - curr_px),
                "position_size_usd": pos_sz,
                "meta": {"target_set": "SET_5"},
            })

        if not candidates:
            continue

        res = engine.execute_stream(
            stream_id=f"SET5_{symbol}",
            symbol=symbol,
            timeframe_set="SET_5",
            hypothesis="MACRO_INTERLOCK",
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

        print(f"  [{symbol:<8}] N={res.total_trades:>3} | WR={res.win_rate*100:>5.1f}% | TotR={res.total_r:>+7.2f}R | PF={res.profit_factor:>5.2f}", flush=True)

    wr = total_wins / max(total_trades, 1) * 100
    pf = gross_win / max(gross_loss, 0.001)
    print(f">> TOTAL: N={total_trades} | WR={wr:.1f}% | Net Return={total_r:+.2f}R | PF={pf:.2f}\n", flush=True)

if __name__ == "__main__":
    run_set_5_interlock_test(target_r_val=3.0, require_4h_keyzone=True)
