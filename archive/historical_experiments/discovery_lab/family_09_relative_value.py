"""
Quantitative Systems Platform (QSP) — Family 9: Relative Value & Statistical Arbitrage.

Implements:
1. 9A Alpha Relative Value: Cointegrated spread mean-reversion & relative momentum
   across cross-asset crypto pairs (SOL/ETH, SOL/BTC, ETH/BTC).
2. Causal simulation with point-in-time accounting across Dev (2021-2022), Val (2023), and OOS (2024-2026).
"""

import os
import sys
import json
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import load_candles


@dataclass
class PairTrade:
    pair: str  # e.g. "SOL/ETH"
    asset_a: str
    asset_b: str
    direction: str  # 'LONG_A_SHORT_B' or 'SHORT_A_LONG_B'
    entry_ts: int
    entry_ratio: float
    entry_z: float
    exit_ts: int
    exit_ratio: float
    exit_z: float
    holding_bars: int
    pnl_r: float
    exit_reason: str


class RelativeValueAlphaEngine:
    """
    Family 9A: Cross-Asset Statistical Arbitrage & Relative Value.
    Trades the normalized log-spread between pairs of major crypto assets.
    """

    PAIRS = [
        ("SOL/USDT", "ETH/USDT", "SOL/ETH"),
        ("SOL/USDT", "BTC/USDT", "SOL/BTC"),
        ("ETH/USDT", "BTC/USDT", "ETH/BTC"),
    ]

    def __init__(
        self,
        lookback_window: int = 60,  # 60 daily bars for rolling mean/std
        entry_z_threshold: float = 2.0,  # Entry at +/- 2.0 standard deviations
        exit_z_threshold: float = 0.2,   # Exit at mean reversion
        stop_loss_z: float = 3.5,        # Catastrophic spread divergence stop
        max_holding_bars: int = 45,      # Maximum holding period
    ):
        self.lookback_window = lookback_window
        self.entry_z_threshold = entry_z_threshold
        self.exit_z_threshold = exit_z_threshold
        self.stop_loss_z = stop_loss_z
        self.max_holding_bars = max_holding_bars

    @staticmethod
    def align_pair_candles(candles_a: List[Candle], candles_b: List[Candle]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Aligns two candle series by timestamp."""
        dict_b = {c.timestamp: c.close for c in candles_b}
        ts_list = []
        p_a_list = []
        p_b_list = []

        for ca in candles_a:
            if ca.timestamp in dict_b:
                ts_list.append(ca.timestamp)
                p_a_list.append(ca.close)
                p_b_list.append(dict_b[ca.timestamp])

        return np.array(ts_list), np.array(p_a_list), np.array(p_b_list)

    def simulate_pair(
        self,
        candles_a: List[Candle],
        candles_b: List[Candle],
        pair_name: str,
        start_ts: int = 0,
        end_ts: int = 9999999999,
        friction_pct: float = 0.003,  # 0.30% round trip across both legs + slippage
    ) -> List[PairTrade]:
        """Runs point-in-time simulation on a pair."""
        ts, p_a, p_b = self.align_pair_candles(candles_a, candles_b)
        n = len(ts)
        if n < self.lookback_window + 10:
            return []

        # Log ratio
        log_ratio = np.log(p_a / p_b)

        # Rolling mean and std
        rolling_mean = np.full(n, np.nan)
        rolling_std = np.full(n, np.nan)

        for i in range(self.lookback_window, n):
            window = log_ratio[i - self.lookback_window:i]
            rolling_mean[i] = np.mean(window)
            rolling_std[i] = np.std(window, ddof=1)

        z_scores = np.full(n, np.nan)
        valid = rolling_std > 1e-6
        z_scores[valid] = (log_ratio[valid] - rolling_mean[valid]) / rolling_std[valid]

        trades: List[PairTrade] = []
        in_pos = False
        pos_dir = ""
        entry_idx = 0
        entry_z = 0.0
        entry_ratio = 0.0

        for i in range(self.lookback_window + 1, n):
            t = ts[i]
            if t < start_ts or t > end_ts:
                continue

            z = z_scores[i - 1]  # Decision using previous bar close (point-in-time)
            curr_ratio = p_a[i] / p_b[i]

            if not in_pos:
                # Long A, Short B when spread is deeply depressed
                if z <= -self.entry_z_threshold:
                    in_pos = True
                    pos_dir = "LONG_A_SHORT_B"
                    entry_idx = i
                    entry_z = z
                    entry_ratio = curr_ratio
                # Short A, Long B when spread is deeply elevated
                elif z >= self.entry_z_threshold:
                    in_pos = True
                    pos_dir = "SHORT_A_LONG_B"
                    entry_idx = i
                    entry_z = z
                    entry_ratio = curr_ratio
            else:
                bars_held = i - entry_idx
                exit_signal = False
                reason = ""

                # Return on ratio
                ratio_return = (curr_ratio - entry_ratio) / entry_ratio
                if pos_dir == "SHORT_A_LONG_B":
                    ratio_return = -ratio_return

                # Check Mean Reversion
                if pos_dir == "LONG_A_SHORT_B" and z >= -self.exit_z_threshold:
                    exit_signal = True
                    reason = "MEAN_REVERSION"
                elif pos_dir == "SHORT_A_LONG_B" and z <= self.exit_z_threshold:
                    exit_signal = True
                    reason = "MEAN_REVERSION"
                # Check Stop Loss
                elif pos_dir == "LONG_A_SHORT_B" and z <= -self.stop_loss_z:
                    exit_signal = True
                    reason = "SPREAD_DIVERGENCE_SL"
                elif pos_dir == "SHORT_A_LONG_B" and z >= self.stop_loss_z:
                    exit_signal = True
                    reason = "SPREAD_DIVERGENCE_SL"
                # Check Max Holding Period
                elif bars_held >= self.max_holding_bars:
                    exit_signal = True
                    reason = "TIME_EXPIRY"

                if exit_signal:
                    net_return = ratio_return - friction_pct
                    # Approximate risk unit R: target stop distance is approximately (stop_loss_z - entry_z) * std
                    # We normalize 1R to a standard 5% spread move
                    r_unit = 0.05
                    pnl_r = net_return / r_unit

                    trades.append(
                        PairTrade(
                            pair=pair_name,
                            asset_a=pair_name.split("/")[0],
                            asset_b=pair_name.split("/")[1],
                            direction=pos_dir,
                            entry_ts=ts[entry_idx],
                            entry_ratio=entry_ratio,
                            entry_z=entry_z,
                            exit_ts=t,
                            exit_ratio=curr_ratio,
                            exit_z=z,
                            holding_bars=bars_held,
                            pnl_r=round(pnl_r, 2),
                            exit_reason=reason,
                        )
                    )
                    in_pos = False

        return trades


def run_family_09_research():
    """Executes backtesting of Family 9 across Development, Validation, and OOS."""
    print("=" * 80)
    print("QUANTITATIVE SYSTEMS PLATFORM — FAMILY 9 RELATIVE VALUE RESEARCH AUDIT")
    print("=" * 80)

    # Epochs
    DEV_START = 1609459200  # 2021-01-01
    DEV_END = 1672531199    # 2022-12-31
    VAL_START = 1672531200  # 2023-01-01
    VAL_END = 1704067199    # 2023-12-31
    OOS_START = 1704067200  # 2024-01-01
    OOS_END = 1773446400    # 2026-03-14

    engine = RelativeValueAlphaEngine(lookback_window=45, entry_z_threshold=1.8, exit_z_threshold=0.2)

    # Load 1D candles
    candles_sol = load_candles("SOL/USDT", "1d") or []
    candles_eth = load_candles("ETH/USDT", "1d") or []
    candles_btc = load_candles("BTC/USDT", "1d") or []

    if not candles_sol or not candles_eth or not candles_btc:
        print("ERROR: Incomplete 1d candle cache for pairs analysis!")
        return

    pairs = [
        (candles_sol, candles_eth, "SOL/ETH"),
        (candles_sol, candles_btc, "SOL/BTC"),
        (candles_eth, candles_btc, "ETH/BTC"),
    ]

    all_results = {}

    for c_a, c_b, pname in pairs:
        trades_dev = engine.simulate_pair(c_a, c_b, pname, DEV_START, DEV_END)
        trades_val = engine.simulate_pair(c_a, c_b, pname, VAL_START, VAL_END)
        trades_oos = engine.simulate_pair(c_a, c_b, pname, OOS_START, OOS_END)

        def calc_metrics(trades: List[PairTrade]) -> Dict[str, Any]:
            if not trades:
                return {"trades": 0, "net_r": 0.0, "win_rate": 0.0, "pf": 0.0, "max_dd": 0.0}
            n = len(trades)
            net_r = sum(t.pnl_r for t in trades)
            wins = [t.pnl_r for t in trades if t.pnl_r > 0]
            losses = [abs(t.pnl_r) for t in trades if t.pnl_r < 0]
            win_rate = len(wins) / n
            pf = sum(wins) / sum(losses) if sum(losses) > 0 else 99.0

            # Drawdown
            equity = 0.0
            peak = 0.0
            max_dd = 0.0
            for t in trades:
                equity += t.pnl_r
                if equity > peak:
                    peak = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd

            return {
                "trades": n,
                "net_r": round(net_r, 2),
                "win_rate": round(win_rate * 100, 1),
                "pf": round(pf, 2),
                "max_dd": round(max_dd, 2),
            }

        m_dev = calc_metrics(trades_dev)
        m_val = calc_metrics(trades_val)
        m_oos = calc_metrics(trades_oos)
        life_r = m_dev["net_r"] + m_val["net_r"] + m_oos["net_r"]

        all_results[pname] = {
            "dev": m_dev,
            "val": m_val,
            "oos": m_oos,
            "lifetime_net_r": round(life_r, 2),
            "total_trades": m_dev["trades"] + m_val["trades"] + m_oos["trades"],
        }

        print(f"\n[PAIR] {pname}:")
        print(f"  Dev (2021-2022): N={m_dev['trades']}, Net R=+{m_dev['net_r']}R, WR={m_dev['win_rate']}%, PF={m_dev['pf']}")
        print(f"  Val (2023):      N={m_val['trades']}, Net R=+{m_val['net_r']}R, WR={m_val['win_rate']}%, PF={m_val['pf']}")
        print(f"  OOS (2024-2026): N={m_oos['trades']}, Net R=+{m_oos['net_r']}R, WR={m_oos['win_rate']}%, PF={m_oos['pf']}")
        print(f"  Lifetime Net R:  {'+' if life_r >= 0 else ''}{life_r:.2f}R")

    # Output JSON summary
    out_json = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results",
        "FAMILY_09_RELATIVE_VALUE_RESEARCH.json",
    )
    with open(out_json, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n[FAMILY 9] Research summary saved to: {out_json}")


if __name__ == "__main__":
    run_family_09_research()
