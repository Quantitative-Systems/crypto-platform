"""Crypto Trading Platform — Systematic Long-Term DCA & Value Investing Strategy Plugin.

Executes rule-based periodic capital accumulation with value and moving-average filters,
designed for long-term systematic investing accounts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class SystematicInvestingStrategy(BaseStrategy):
    """Dollar-Cost Averaging (DCA) systematic investing plugin."""

    def __init__(
        self,
        strategy_id: str = "sys_investing_dca_v1",
        horizon: str = "INVEST",
        supported_symbols: Optional[List[str]] = None,
        allocation_per_interval_usd: float = 500.0,
        ma_filter_bars: int = 50,
        interval_bars: int = 24,  # e.g. every 24 bars (e.g. daily on 1h or monthly on 1d)
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="INVEST",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.allocation_per_interval_usd = allocation_per_interval_usd
        self.ma_filter_bars = ma_filter_bars
        self.interval_bars = interval_bars
        self._bars_since_last_invest: Dict[str, int] = {}

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        history = self.recent_candles.setdefault(event.symbol, [])
        history.append(event)
        if len(history) > self.ma_filter_bars + 10:
            history.pop(0)

        elapsed = self._bars_since_last_invest.get(event.symbol, self.interval_bars)
        self._bars_since_last_invest[event.symbol] = elapsed + 1

        if self._bars_since_last_invest[event.symbol] < self.interval_bars:
            return []

        if len(history) < self.ma_filter_bars:
            return []

        closes = np.array([c.close for c in history])
        current_close = closes[-1]
        ma = float(np.mean(closes[-self.ma_filter_bars:]))

        # Value DCA logic: increase size if trading below MA, reduce if extended
        discount_ratio = ma / current_close if current_close > 0 else 1.0
        multiplier = float(np.clip(discount_ratio, 0.5, 2.0))

        actual_usd = self.allocation_per_interval_usd * multiplier
        target_size = actual_usd / current_close

        # Reset interval counter
        self._bars_since_last_invest[event.symbol] = 0

        return [
            self.create_intent(
                symbol=event.symbol,
                direction=1,  # Long accumulation
                target_size=round(target_size, 4),
                urgency=ExecutionUrgency.LOW,
                limit_price=current_close,
                stop_price=None,  # Long term investing hold
                target_price=None,
                reason=f"Systematic DCA: ${actual_usd:.2f} allocated (multiplier {multiplier:.2f}x vs MA)",
            )
        ]
