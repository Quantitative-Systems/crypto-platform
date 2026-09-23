"""Crypto Trading Platform — Trend & Volatility Breakout Strategy.

Identifies multi-candle channel breakouts accompanied by volatility expansion.
Generates structural limit/market entries with defined stop-loss levels.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class TrendBreakoutStrategy(BaseStrategy):
    """Donchian channel breakout with ATR-based risk boundaries."""

    def __init__(
        self,
        strategy_id: str = "trend_breakout_v1",
        horizon: str = "INTRADAY",
        supported_symbols: Optional[List[str]] = None,
        lookback: int = 20,
        atr_mult: float = 1.5,
        target_r: float = 2.0,
        risk_per_trade_usd: float = 250.0,
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="TREND",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.lookback = lookback
        self.atr_mult = atr_mult
        self.target_r = target_r
        self.risk_per_trade_usd = risk_per_trade_usd

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        history = self.recent_candles.setdefault(event.symbol, [])
        history.append(event)
        if len(history) > self.lookback + 20:
            history.pop(0)

        if len(history) < self.lookback + 1:
            return []

        # Calculate high/low channels and ATR
        highs = np.array([c.high for c in history[:-1]])
        lows = np.array([c.low for c in history[:-1]])
        closes = np.array([c.close for c in history[:-1]])

        highest_high = np.max(highs[-self.lookback:])
        lowest_low = np.min(lows[-self.lookback:])

        # Simple ATR calculation
        if len(highs) > 1:
            tr = np.maximum(
                highs[1:] - lows[1:],
                np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])),
            )
            atr = float(np.mean(tr))
        else:
            atr = float(event.high - event.low)

        if atr <= 0:
            atr = float(event.close * 0.01)  # Fallback 1% of price

        curr_close = event.close
        stop_dist = self.atr_mult * atr
        # Size so that risk = risk_per_trade_usd
        target_size = self.risk_per_trade_usd / stop_dist

        intents: List[OrderIntent] = []

        # Long breakout
        if curr_close > highest_high and self.active_positions.get(event.symbol, 0.0) <= 0:
            stop_px = curr_close - stop_dist
            target_px = curr_close + self.target_r * stop_dist
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=1,
                    target_size=target_size,
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=curr_close,
                    stop_price=stop_px,
                    target_price=target_px,
                    reason=f"Breakout above {highest_high:.2f}",
                )
            )

        # Short breakout
        elif curr_close < lowest_low and self.active_positions.get(event.symbol, 0.0) >= 0:
            stop_px = curr_close + stop_dist
            target_px = curr_close - self.target_r * stop_dist
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=-1,
                    target_size=target_size,
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=curr_close,
                    stop_price=stop_px,
                    target_price=target_px,
                    reason=f"Breakdown below {lowest_low:.2f}",
                )
            )

        return intents
