"""Crypto Trading Platform — Volatility Expansion Strategy Plugin.

Monitors ATR (Average True Range) compression and enters aggressively on volatility expansion,
targeting large regime shifts with trailing profit locks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class VolatilityExpansionStrategy(BaseStrategy):
    """ATR expansion strategy plugin."""

    def __init__(
        self,
        strategy_id: str = "vol_expansion_v1",
        horizon: str = "SWING",
        supported_symbols: Optional[List[str]] = None,
        atr_period: int = 14,
        expansion_factor: float = 1.8,
        risk_per_trade_usd: float = 250.0,
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="VOLATILITY",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.atr_period = atr_period
        self.expansion_factor = expansion_factor
        self.risk_per_trade_usd = risk_per_trade_usd

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        history = self.recent_candles.setdefault(event.symbol, [])
        history.append(event)
        if len(history) > self.atr_period + 20:
            history.pop(0)

        if len(history) < self.atr_period + 2:
            return []

        # Calculate True Range series
        highs = np.array([c.high for c in history])
        lows = np.array([c.low for c in history])
        closes = np.array([c.close for c in history])

        prev_closes = closes[:-1]
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(abs(highs[1:] - prev_closes), abs(lows[1:] - prev_closes)),
        )

        recent_tr = tr[-1]
        baseline_atr = float(np.mean(tr[-self.atr_period - 1: -1]))

        if baseline_atr <= 0:
            return []

        current_close = closes[-1]
        current_pos = self.active_positions.get(event.symbol, 0.0)
        intents = []

        # Volatility expansion trigger
        if recent_tr >= baseline_atr * self.expansion_factor and current_pos == 0:
            # Check direction of expansion bar
            bar_open = history[-1].open
            if current_close > bar_open:
                # Bullish expansion
                stop_price = current_close - baseline_atr * 1.5
                target_price = current_close + baseline_atr * 3.0
                target_size = self.risk_per_trade_usd / max(1.0, current_close - stop_price)

                intents.append(
                    self.create_intent(
                        symbol=event.symbol,
                        direction=1,
                        target_size=round(target_size, 4),
                        urgency=ExecutionUrgency.HIGH,
                        limit_price=current_close,
                        stop_price=stop_price,
                        target_price=target_price,
                        reason=f"Bullish volatility expansion: TR {recent_tr:.2f} >= {self.expansion_factor}x ATR",
                    )
                )

            elif current_close < bar_open:
                # Bearish expansion
                stop_price = current_close + baseline_atr * 1.5
                target_price = current_close - baseline_atr * 3.0
                target_size = self.risk_per_trade_usd / max(1.0, stop_price - current_close)

                intents.append(
                    self.create_intent(
                        symbol=event.symbol,
                        direction=-1,
                        target_size=round(target_size, 4),
                        urgency=ExecutionUrgency.HIGH,
                        limit_price=current_close,
                        stop_price=stop_price,
                        target_price=target_price,
                        reason=f"Bearish volatility expansion: TR {recent_tr:.2f} >= {self.expansion_factor}x ATR",
                    )
                )

        return intents
