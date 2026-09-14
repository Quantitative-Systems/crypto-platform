"""
PROJECT TOP1 — Multi-Family Strategy Generation & Execution Engine.

Implements high-performance, causally strict trading strategy logic across the 8 required families:
Family 1: Trend Following (Hierarchical EMA trend + dynamic ATR stop)
Family 2: Trend + Pullback (HTF EMA trend + MTF RSI pullback + LTF confirmation)
Family 3: Breakout (Donchian channel breakout with volume expansion)
Family 4: Momentum (Multi-timeframe momentum impulse)
Family 5: Mean Reversion (Bollinger Band extreme exhaustion + snapback)
Family 6: Volatility Expansion (Bollinger Squeeze breakout)
Family 7: Multi-Timeframe Continuation (HTF trend + MTF structure + LTF breakout)
Family 8: Regime-Adaptive Systems (ADX regime classification + adaptive routing)

All strategies obey:
- Strict zero lookahead (signals confirmed on candle close, execution at close price)
- Certified friction-adjusted sizing (initial stop loss <= 1.000% equity inclusive of taker fee, slippage, spread)
- Adverse-first intra-bar collision logic
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from market_intelligence.primitives import Candle
from backtesting.friction_model import FrictionModel
from research.analytics.r_accounting import RAccountingEngine
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.fast_indicators_extended import (
    ema_numpy, atr_numpy, rsi_numpy, donchian_numpy,
    bollinger_bands_numpy, adx_numpy
)


class StrategyExecutor:
    """Standardized causal backtester for discovery lab strategy families."""

    def __init__(
        self,
        symbol: str,
        set_name: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        starting_balance: float = 10000.0,
        risk_pct: float = 0.01,
        start_ts: int = OOSManager.DEV_START_TS,
        end_ts: int = OOSManager.DEV_END_TS,
    ):
        self.symbol = symbol
        self.set_name = set_name
        self.htf_candles = htf_candles
        self.mtf_candles = mtf_candles
        self.ltf_candles = ltf_candles
        self.starting_balance = starting_balance
        self.risk_pct = risk_pct
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.friction = FrictionModel()

    def _sync_to_ltf(self, htf_ts: np.ndarray, htf_data: np.ndarray, ltf_ts: np.ndarray) -> np.ndarray:
        """Forward-fills HTF/MTF data onto LTF timestamps with zero lookahead."""
        idx = np.searchsorted(htf_ts, ltf_ts, side='right') - 1
        valid_mask = idx >= 0
        res = np.full(len(ltf_ts), np.nan, dtype=np.float64)
        res[valid_mask] = htf_data[idx[valid_mask]]
        return res

    def simulate_signals(
        self,
        long_signals: np.ndarray,
        short_signals: np.ndarray,
        sl_distances: np.ndarray,
        tp_multipliers: float = 2.5,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Simulates execution given entry signals and stop loss distances.
        Strictly applies adverse-first collisions, friction, and R-accounting.
        """
        eval_start_ts = start_ts if start_ts is not None else self.start_ts
        eval_end_ts = end_ts if end_ts is not None else self.end_ts
        n = len(self.ltf_candles)
        if n == 0:
            return {"trades": [], "metrics": RAccountingEngine.compute_stream_metrics([])}

        highs = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        lows = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        closes = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        timestamps = np.array([c.timestamp for c in self.ltf_candles], dtype=np.int64)

        balance = self.starting_balance
        trades = []
        active_pos = None
        trade_counter = 0

        for i in range(50, n):
            if balance <= 0:
                break

            current_ts = timestamps[i]
            c_high = highs[i]
            c_low = lows[i]

            # 1. Manage existing active position
            if active_pos is not None:
                d = active_pos["direction"]
                sl = active_pos["sl"]
                tp = active_pos["tp"]

                # Track excursions
                if d == 1:
                    active_pos["mfe_price"] = max(active_pos["mfe_price"], c_high)
                    active_pos["mae_price"] = min(active_pos["mae_price"], c_low)
                    hit_sl = c_low <= sl
                    hit_tp = c_high >= tp
                else:
                    active_pos["mfe_price"] = min(active_pos["mfe_price"], c_low)
                    active_pos["mae_price"] = max(active_pos["mae_price"], c_high)
                    hit_sl = c_high >= sl
                    hit_tp = c_low <= tp

                exit_price = None
                exit_reason = None

                # Adverse-first collision rule: If both hit on same candle, SL is executed
                if hit_sl and hit_tp:
                    exit_price = sl
                    exit_reason = "SL_COLLISION"
                elif hit_sl:
                    exit_price = sl
                    exit_reason = "STOP_LOSS"
                elif hit_tp:
                    exit_price = tp
                    exit_reason = "TAKE_PROFIT"

                if exit_price is not None:
                    pos = active_pos
                    if d == 1:
                        fill_exit = self.friction.calculate_sell_fill(exit_price)
                        raw_pnl = (fill_exit - pos["fill_entry"]) * pos["size"]
                    else:
                        fill_exit = self.friction.calculate_buy_fill(exit_price)
                        raw_pnl = (pos["fill_entry"] - fill_exit) * pos["size"]

                    exit_fee = self.friction.calculate_fee(fill_exit * pos["size"])
                    net_pnl = raw_pnl - pos["entry_fee"] - exit_fee
                    balance += net_pnl

                    realized_r = RAccountingEngine.calculate_trade_r(net_pnl, pos["entry_equity"], self.risk_pct)
                    mfe_r, mae_r = RAccountingEngine.calculate_excursions(
                        d, pos["entry_price"], pos["initial_sl"], pos["mfe_price"], pos["mae_price"]
                    )

                    trades.append({
                        "trade_id": pos["id"],
                        "symbol": self.symbol,
                        "set": self.set_name,
                        "direction": d,
                        "entry_ts": pos["entry_ts"],
                        "entry_equity": pos["entry_equity"],
                        "entry_price": pos["entry_price"],
                        "fill_entry": pos["fill_entry"],
                        "size": pos["size"],
                        "entry_fee": pos["entry_fee"],
                        "initial_sl": pos["initial_sl"],
                        "tp": pos["tp"],
                        "planned_r": pos["planned_r"],
                        "exit_ts": current_ts,
                        "exit_price": exit_price,
                        "fill_exit": fill_exit,
                        "exit_reason": exit_reason,
                        "exit_fee": exit_fee,
                        "net_pnl": net_pnl,
                        "realized_r": realized_r,
                        "mfe_r": mfe_r,
                        "mae_r": mae_r,
                    })
                    active_pos = None

            # 2. Check for new entry signals
            if active_pos is None:
                d = 0
                if long_signals[i]:
                    d = 1
                elif short_signals[i]:
                    d = -1

                if d != 0:
                    entry_price = closes[i]
                    sl_dist = sl_distances[i]
                    if np.isnan(sl_dist) or sl_dist <= 0:
                        continue

                    if d == 1:
                        sl_price = entry_price - sl_dist
                        tp_price = entry_price + (sl_dist * tp_multipliers)
                        fill_entry = self.friction.calculate_buy_fill(entry_price)
                        fill_sl_exit = self.friction.calculate_sell_fill(sl_price)
                        unit_loss = (fill_entry - fill_sl_exit) + self.friction.calculate_fee(fill_entry) + self.friction.calculate_fee(fill_sl_exit)
                    else:
                        sl_price = entry_price + sl_dist
                        tp_price = entry_price - (sl_dist * tp_multipliers)
                        fill_entry = self.friction.calculate_sell_fill(entry_price)
                        fill_sl_exit = self.friction.calculate_buy_fill(sl_price)
                        unit_loss = (fill_sl_exit - fill_entry) + self.friction.calculate_fee(fill_entry) + self.friction.calculate_fee(fill_sl_exit)

                    if unit_loss <= 0:
                        continue

                    trade_counter += 1
                    max_dollar_loss = balance * self.risk_pct
                    position_size = max_dollar_loss / unit_loss
                    entry_fee = self.friction.calculate_fee(fill_entry * position_size)

                    active_pos = {
                        "id": f"{self.symbol}_{self.set_name}_{trade_counter}",
                        "direction": d,
                        "entry_ts": current_ts,
                        "entry_equity": balance,
                        "entry_price": entry_price,
                        "fill_entry": fill_entry,
                        "size": position_size,
                        "entry_fee": entry_fee,
                        "initial_sl": sl_price,
                        "sl": sl_price,
                        "tp": tp_price,
                        "planned_r": tp_multipliers,
                        "mfe_price": entry_price,
                        "mae_price": entry_price,
                    }

        # Filter strictly to specified evaluation window
        eval_trades = OOSManager.filter_trades_to_window(trades, eval_start_ts, eval_end_ts)
        metrics = RAccountingEngine.compute_stream_metrics(eval_trades)

        return {
            "symbol": self.symbol,
            "set": self.set_name,
            "total_trades_all_time": len(trades),
            "total_trades_dev": len(eval_trades),
            "trades": eval_trades,
            "metrics": metrics,
        }

    # =========================================================================
    # Strategy Families Implementations
    # =========================================================================

    def run_family_1_trend_following(self, tp_r: float = 3.0, atr_mult: float = 2.0) -> Dict[str, Any]:
        """Family 1: Trend Following (Hierarchical EMA trend + ATR stop)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        ltf_ts = np.array([c.timestamp for c in self.ltf_candles], dtype=np.int64)

        htf_c = np.array([c.close for c in self.htf_candles], dtype=np.float64)
        htf_ts = np.array([c.timestamp for c in self.htf_candles], dtype=np.int64)
        htf_ema50 = ema_numpy(htf_c, 50)
        htf_trend_long = self._sync_to_ltf(htf_ts, (htf_c > htf_ema50).astype(np.float64), ltf_ts) == 1.0
        htf_trend_short = self._sync_to_ltf(htf_ts, (htf_c < htf_ema50).astype(np.float64), ltf_ts) == 1.0

        ltf_ema20 = ema_numpy(ltf_c, 20)
        ltf_ema50 = ema_numpy(ltf_c, 50)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        long_signals = (
            htf_trend_long &
            (ltf_c > ltf_ema20) &
            (ltf_ema20 > ltf_ema50) &
            (np.roll(ltf_c, 1) <= np.roll(ltf_ema20, 1))  # Fresh breakout cross
        )
        short_signals = (
            htf_trend_short &
            (ltf_c < ltf_ema20) &
            (ltf_ema20 < ltf_ema50) &
            (np.roll(ltf_c, 1) >= np.roll(ltf_ema20, 1))
        )
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_2_trend_pullback(self, tp_r: float = 2.5, atr_mult: float = 1.5) -> Dict[str, Any]:
        """Family 2: Trend + Pullback (HTF EMA trend + MTF RSI pullback + LTF confirmation)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        ltf_ts = np.array([c.timestamp for c in self.ltf_candles], dtype=np.int64)

        htf_c = np.array([c.close for c in self.htf_candles], dtype=np.float64)
        htf_ts = np.array([c.timestamp for c in self.htf_candles], dtype=np.int64)
        htf_ema50 = ema_numpy(htf_c, 50)
        htf_bull = self._sync_to_ltf(htf_ts, (htf_c > htf_ema50).astype(np.float64), ltf_ts) == 1.0
        htf_bear = self._sync_to_ltf(htf_ts, (htf_c < htf_ema50).astype(np.float64), ltf_ts) == 1.0

        mtf_c = np.array([c.close for c in self.mtf_candles], dtype=np.float64)
        mtf_ts = np.array([c.timestamp for c in self.mtf_candles], dtype=np.int64)
        mtf_rsi = rsi_numpy(mtf_c, 14)
        mtf_pb_long = self._sync_to_ltf(mtf_ts, (mtf_rsi <= 40.0).astype(np.float64), ltf_ts) == 1.0
        mtf_pb_short = self._sync_to_ltf(mtf_ts, (mtf_rsi >= 60.0).astype(np.float64), ltf_ts) == 1.0

        ltf_rsi = rsi_numpy(ltf_c, 14)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        long_signals = htf_bull & mtf_pb_long & (ltf_rsi > 45.0) & (np.roll(ltf_rsi, 1) <= 45.0)
        short_signals = htf_bear & mtf_pb_short & (ltf_rsi < 55.0) & (np.roll(ltf_rsi, 1) >= 55.0)
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_3_breakout(self, period: int = 20, tp_r: float = 3.0, atr_mult: float = 1.5) -> Dict[str, Any]:
        """Family 3: Breakout (Donchian Channel breakout with volume confirmation)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        ltf_v = np.array([c.volume for c in self.ltf_candles], dtype=np.float64)

        d_upper, d_lower, d_mid = donchian_numpy(ltf_h, ltf_l, period=period)
        vol_sma = ema_numpy(ltf_v, 20)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        vol_conf = ltf_v > (vol_sma * 1.1)
        long_signals = (ltf_c > d_upper) & vol_conf
        short_signals = (ltf_c < d_lower) & vol_conf
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_4_momentum(self, tp_r: float = 2.5, atr_mult: float = 1.5) -> Dict[str, Any]:
        """Family 4: Momentum (ROC + RSI continuation)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)

        rsi = rsi_numpy(ltf_c, 14)
        ema20 = ema_numpy(ltf_c, 20)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        roc = np.zeros_like(ltf_c)
        roc[10:] = (ltf_c[10:] - ltf_c[:-10]) / ltf_c[:-10] * 100.0

        long_signals = (roc > 1.5) & (rsi > 55.0) & (ltf_c > ema20) & (np.roll(roc, 1) <= 1.5)
        short_signals = (roc < -1.5) & (rsi < 45.0) & (ltf_c < ema20) & (np.roll(roc, 1) >= -1.5)
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_5_mean_reversion(self, tp_r: float = 1.8, atr_mult: float = 1.2) -> Dict[str, Any]:
        """Family 5: Mean Reversion (Bollinger Band extreme exhaustion + snapback)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)

        bb_mid, bb_upper, bb_lower = bollinger_bands_numpy(ltf_c, 20, 2.0)
        rsi = rsi_numpy(ltf_c, 14)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        # Long: candle was below lower band, now closes back above it, with RSI < 35
        long_signals = (np.roll(ltf_c, 1) < np.roll(bb_lower, 1)) & (ltf_c >= bb_lower) & (rsi < 40.0)
        # Short: candle was above upper band, now closes back below it, with RSI > 65
        short_signals = (np.roll(ltf_c, 1) > np.roll(bb_upper, 1)) & (ltf_c <= bb_upper) & (rsi > 60.0)
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_6_volatility_expansion(self, tp_r: float = 3.0, atr_mult: float = 1.5) -> Dict[str, Any]:
        """Family 6: Volatility Expansion (Bollinger Band squeeze breakout)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)

        bb_mid, bb_upper, bb_lower = bollinger_bands_numpy(ltf_c, 20, 2.0)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        bandwidth = (bb_upper - bb_lower) / bb_mid
        bw_sma = ema_numpy(bandwidth, 20)
        is_squeeze = bandwidth < (bw_sma * 0.85)

        long_signals = np.roll(is_squeeze, 1) & (ltf_c > bb_upper)
        short_signals = np.roll(is_squeeze, 1) & (ltf_c < bb_lower)
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)

    def run_family_7_mtf_continuation(
        self,
        tp_r: float = 2.5,
        atr_mult: float = 1.5,
        ema_len: int = 21,
        donchian_len: int = 10,
    ) -> Dict[str, Any]:
        """Family 7: Multi-Timeframe Continuation (HTF trend + MTF trend + LTF local swing break)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        ltf_ts = np.array([c.timestamp for c in self.ltf_candles], dtype=np.int64)

        htf_c = np.array([c.close for c in self.htf_candles], dtype=np.float64)
        htf_ts = np.array([c.timestamp for c in self.htf_candles], dtype=np.int64)
        htf_ema = ema_numpy(htf_c, ema_len)
        htf_bull = self._sync_to_ltf(htf_ts, (htf_c > htf_ema).astype(np.float64), ltf_ts) == 1.0
        htf_bear = self._sync_to_ltf(htf_ts, (htf_c < htf_ema).astype(np.float64), ltf_ts) == 1.0

        mtf_c = np.array([c.close for c in self.mtf_candles], dtype=np.float64)
        mtf_ts = np.array([c.timestamp for c in self.mtf_candles], dtype=np.int64)
        mtf_ema = ema_numpy(mtf_c, ema_len)
        mtf_bull = self._sync_to_ltf(mtf_ts, (mtf_c > mtf_ema).astype(np.float64), ltf_ts) == 1.0
        mtf_bear = self._sync_to_ltf(mtf_ts, (mtf_c < mtf_ema).astype(np.float64), ltf_ts) == 1.0

        d_upper, d_lower, _ = donchian_numpy(ltf_h, ltf_l, period=donchian_len)
        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)

        long_signals = htf_bull & mtf_bull & (ltf_c > d_upper)
        short_signals = htf_bear & mtf_bear & (ltf_c < d_lower)
        long_signals[:50] = False
        short_signals[:50] = False

        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)


    def run_family_8_regime_adaptive(self, tp_r: float = 2.5, atr_mult: float = 1.5) -> Dict[str, Any]:
        """Family 8: Regime-Adaptive (ADX trend vs range classifier routing)."""
        ltf_c = np.array([c.close for c in self.ltf_candles], dtype=np.float64)
        ltf_h = np.array([c.high for c in self.ltf_candles], dtype=np.float64)
        ltf_l = np.array([c.low for c in self.ltf_candles], dtype=np.float64)
        ltf_ts = np.array([c.timestamp for c in self.ltf_candles], dtype=np.int64)

        htf_c = np.array([c.close for c in self.htf_candles], dtype=np.float64)
        htf_h = np.array([c.high for c in self.htf_candles], dtype=np.float64)
        htf_l = np.array([c.low for c in self.htf_candles], dtype=np.float64)
        htf_ts = np.array([c.timestamp for c in self.htf_candles], dtype=np.int64)

        htf_adx = adx_numpy(htf_h, htf_l, htf_c, 14)
        is_trending = self._sync_to_ltf(htf_ts, (htf_adx > 25.0).astype(np.float64), ltf_ts) == 1.0

        # Sub-strategy 1 (Trending): EMA crossover
        ltf_ema20 = ema_numpy(ltf_c, 20)
        ltf_ema50 = ema_numpy(ltf_c, 50)
        trend_long = is_trending & (ltf_c > ltf_ema20) & (ltf_ema20 > ltf_ema50) & (np.roll(ltf_c, 1) <= np.roll(ltf_ema20, 1))
        trend_short = is_trending & (ltf_c < ltf_ema20) & (ltf_ema20 < ltf_ema50) & (np.roll(ltf_c, 1) >= np.roll(ltf_ema20, 1))

        # Sub-strategy 2 (Ranging): BB Mean Reversion
        bb_mid, bb_upper, bb_lower = bollinger_bands_numpy(ltf_c, 20, 2.0)
        range_long = (~is_trending) & (np.roll(ltf_c, 1) < np.roll(bb_lower, 1)) & (ltf_c >= bb_lower)
        range_short = (~is_trending) & (np.roll(ltf_c, 1) > np.roll(bb_upper, 1)) & (ltf_c <= bb_upper)

        long_signals = trend_long | range_long
        short_signals = trend_short | range_short
        long_signals[:50] = False
        short_signals[:50] = False

        atr = atr_numpy(ltf_h, ltf_l, ltf_c, 14)
        sl_dist = atr * atr_mult
        return self.simulate_signals(long_signals, short_signals, sl_dist, tp_multipliers=tp_r)
