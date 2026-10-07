"""Crypto Trading Platform — Time-Series & Cross-Sectional Momentum Strategy Plugin.

Evaluates multi-period price momentum and relative strength to generate
directional position intents with dynamic volatility-scaled risk sizing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """Multi-timeframe momentum strategy plugin."""

    def __init__(
        self,
        strategy_id: str = "momentum_v1",
        horizon: str = "SWING",
        supported_symbols: Optional[List[str]] = None,
        lookback_bars: int = 24,
        momentum_threshold_pct: float = 0.02,
        risk_per_trade_usd: float = 300.0,
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="MOMENTUM",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.lookback_bars = lookback_bars
        self.momentum_threshold_pct = momentum_threshold_pct
        self.risk_per_trade_usd = risk_per_trade_usd

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        history = self.recent_candles.setdefault(event.symbol, [])
        history.append(event)
        if len(history) > self.lookback_bars + 10:
            history.pop(0)

        if len(history) < self.lookback_bars + 1:
            return []

        closes = np.array([c.close for c in history])
        current_close = closes[-1]
        past_close = closes[-1 - self.lookback_bars]

        pct_change = (current_close - past_close) / past_close
        current_pos = self.active_positions.get(event.symbol, 0.0)

        intents = []
        if pct_change >= self.momentum_threshold_pct and current_pos <= 0:
            # Bullish momentum signal
            stop_price = current_close * 0.97
            target_price = current_close * 1.06
            target_size = self.risk_per_trade_usd / max(1.0, current_close - stop_price)

            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=1,
                    target_size=round(target_size, 4),
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=current_close,
                    stop_price=stop_price,
                    target_price=target_price,
                    reason=f"Bullish momentum: +{pct_change*100:.2f}% over {self.lookback_bars} bars",
                )
            )

        elif pct_change <= -self.momentum_threshold_pct and current_pos >= 0:
            # Bearish momentum signal
            stop_price = current_close * 1.03
            target_price = current_close * 0.94
            target_size = self.risk_per_trade_usd / max(1.0, stop_price - current_close)

            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=-1,
                    target_size=round(target_size, 4),
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=current_close,
                    stop_price=stop_price,
                    target_price=target_price,
                    reason=f"Bearish momentum: {pct_change*100:.2f}% over {self.lookback_bars} bars",
                )
            )

        return intents
