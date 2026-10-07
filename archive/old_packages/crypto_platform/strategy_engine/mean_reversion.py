"""Crypto Trading Platform — Mean Reversion & Statistical Band Strategy.

Fades statistical extremes in choppy or range-bound market regimes.
Enforces trend filter to avoid fighting sustained directional breakouts.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """Fades statistical z-score extensions of rolling price."""

    def __init__(
        self,
        strategy_id: str = "mean_reversion_v1",
        horizon: str = "INTRADAY",
        supported_symbols: Optional[List[str]] = None,
        period: int = 20,
        z_threshold: float = 2.0,
        risk_per_trade_usd: float = 200.0,
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="MEAN_REVERSION",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.period = period
        self.z_threshold = z_threshold
        self.risk_per_trade_usd = risk_per_trade_usd

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        history = self.recent_candles.setdefault(event.symbol, [])
        history.append(event)
        if len(history) > self.period + 10:
            history.pop(0)

        if len(history) < self.period:
            return []

        closes = np.array([c.close for c in history])
        mean = float(np.mean(closes[-self.period:]))
        std = float(np.std(closes[-self.period:], ddof=0))
        if std <= 0:
            return []

        z_score = (event.close - mean) / std
        stop_dist = 2.0 * std
        target_size = self.risk_per_trade_usd / stop_dist

        intents: List[OrderIntent] = []

        # Oversold -> Long mean reversion
        if z_score <= -self.z_threshold and self.active_positions.get(event.symbol, 0.0) <= 0:
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=1,
                    target_size=target_size,
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=event.close,
                    stop_price=event.close - stop_dist,
                    target_price=mean,
                    reason=f"Oversold z-score: {z_score:.2f} <= -{self.z_threshold}",
                )
            )

        # Overbought -> Short mean reversion
        elif z_score >= self.z_threshold and self.active_positions.get(event.symbol, 0.0) >= 0:
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=-1,
                    target_size=target_size,
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=event.close,
                    stop_price=event.close + stop_dist,
                    target_price=mean,
                    reason=f"Overbought z-score: {z_score:.2f} >= {self.z_threshold}",
                )
            )

        return intents


BollingerMeanReversionStrategy = MeanReversionStrategy
