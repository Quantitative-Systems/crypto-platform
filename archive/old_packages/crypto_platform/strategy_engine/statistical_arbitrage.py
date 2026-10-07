"""Crypto Trading Platform — Statistical Arbitrage & Pairs Trading Strategy Plugin.

Evaluates rolling price ratio and normalized z-score spread between correlated asset pairs.
Enters mean-reverting positions when spread exceeds statistical divergence threshold (e.g. |z| >= 2.0).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent
from .base import BaseStrategy


class PairsTradingStrategy(BaseStrategy):
    """Statistical Arbitrage / Pairs Trading Strategy Plugin."""

    def __init__(
        self,
        strategy_id: str = "stat_arb_pairs_v1",
        horizon: str = "INTRADAY",
        asset_a: str = "ETHUSDT",
        asset_b: str = "BTCUSDT",
        lookback_bars: int = 40,
        z_threshold: float = 2.0,
        risk_per_trade_usd: float = 250.0,
    ):
        super().__init__(
            strategy_id=strategy_id,
            family="STAT_ARB",
            horizon=horizon,
            supported_symbols=[asset_a, asset_b],
        )
        self.asset_a = asset_a
        self.asset_b = asset_b
        self.lookback_bars = lookback_bars
        self.z_threshold = z_threshold
        self.risk_per_trade_usd = risk_per_trade_usd
        self._pair_closes: Dict[str, List[float]] = {asset_a: [], asset_b: []}

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        if event.symbol not in self.supported_symbols:
            return []

        series = self._pair_closes[event.symbol]
        series.append(event.close)
        if len(series) > self.lookback_bars + 10:
            series.pop(0)

        # Check if both assets have sufficient synced bars
        if (
            len(self._pair_closes[self.asset_a]) < self.lookback_bars
            or len(self._pair_closes[self.asset_b]) < self.lookback_bars
        ):
            return []

        closes_a = np.array(self._pair_closes[self.asset_a][-self.lookback_bars:])
        closes_b = np.array(self._pair_closes[self.asset_b][-self.lookback_bars:])

        ratio = closes_a / closes_b
        mean_ratio = float(np.mean(ratio))
        std_ratio = float(np.std(ratio))
        if std_ratio <= 1e-8:
            return []

        current_ratio = ratio[-1]
        z_score = (current_ratio - mean_ratio) / std_ratio

        intents = []
        pos_a = self.active_positions.get(self.asset_a, 0.0)

        if z_score >= self.z_threshold and pos_a >= 0:
            # Spread is too high: Short Asset A, Long Asset B
            close_a = closes_a[-1]
            size_a = self.risk_per_trade_usd / (close_a * 0.05)
            intents.append(
                self.create_intent(
                    symbol=self.asset_a,
                    direction=-1,
                    target_size=round(size_a, 4),
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=close_a,
                    stop_price=close_a * 1.04,
                    target_price=close_a * 0.96,
                    reason=f"Pairs stat-arb: z-score +{z_score:.2f} >= +{self.z_threshold}",
                )
            )

        elif z_score <= -self.z_threshold and pos_a <= 0:
            # Spread is too low: Long Asset A, Short Asset B
            close_a = closes_a[-1]
            size_a = self.risk_per_trade_usd / (close_a * 0.05)
            intents.append(
                self.create_intent(
                    symbol=self.asset_a,
                    direction=1,
                    target_size=round(size_a, 4),
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=close_a,
                    stop_price=close_a * 0.96,
                    target_price=close_a * 1.04,
                    reason=f"Pairs stat-arb: z-score {z_score:.2f} <= -{self.z_threshold}",
                )
            )

        return intents
