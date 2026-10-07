"""Crypto Trading Platform — Delta-Hedged Funding Rate Carry Strategy Plugin.

Harvests positive funding payments from perpetual contracts while maintaining
a delta-neutral hedge with spot/synthetic assets.
Includes strict guardrails:
- Trailing 7-day funding APR entry threshold (default: >= 8.0% APR)
- Early exit on funding inversion (funding rate < 0) or compression (< 2.0% APR)
- Capital allocation limits
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.domain import ExecutionUrgency, OrderIntent
from crypto_platform.core.events import CandleEvent, FundingRateEvent
from .base import BaseStrategy


class FundingCarryStrategy(BaseStrategy):
    """Delta-neutral funding harvest strategy plugin."""

    def __init__(
        self,
        strategy_id: str = "funding_carry_v1",
        horizon: str = "CARRY",
        supported_symbols: Optional[List[str]] = None,
        min_entry_apr: float = 0.08,    # 8.0% APR to enter
        min_exit_apr: float = 0.02,     # 2.0% APR to exit
        target_allocation_usd: float = 20_000.0,
    ):
        symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        super().__init__(
            strategy_id=strategy_id,
            family="CARRY",
            horizon=horizon,
            supported_symbols=symbols,
        )
        self.min_entry_apr = min_entry_apr
        self.min_exit_apr = min_exit_apr
        self.target_allocation_usd = target_allocation_usd
        self._funding_rates: Dict[str, List[float]] = {}

    def on_funding_rate(self, event: FundingRateEvent) -> List[OrderIntent]:
        """Track incoming funding payments and evaluate entry/exit."""
        rates = self._funding_rates.setdefault(event.symbol, [])
        rates.append(event.funding_rate)
        if len(rates) > 21:  # 21 periods = 7 days (3 per day)
            rates.pop(0)

        if len(rates) < 6:
            return []

        # Annualized rolling funding yield
        avg_rate_8h = float(np.mean(rates))
        annualized_apr = avg_rate_8h * 3 * 365.0

        current_pos = self.active_positions.get(event.symbol, 0.0)
        intents = []

        # 1. Entry Condition: High positive funding and no existing short position
        if annualized_apr >= self.min_entry_apr and current_pos >= 0:
            target_size = self.target_allocation_usd / max(1.0, event.mark_price)
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=-1,  # Short perpetual leg to receive funding
                    target_size=round(target_size, 4),
                    urgency=ExecutionUrgency.LOW,
                    limit_price=event.mark_price,
                    stop_price=None,  # Delta-hedged; risk managed by basis and funding governor
                    target_price=None,
                    reason=f"Funding carry entry: APR {annualized_apr*100:.2f}% >= {self.min_entry_apr*100:.2f}%",
                )
            )

        # 2. Exit Condition: Funding turns negative or compresses below threshold
        elif (annualized_apr <= self.min_exit_apr or avg_rate_8h < 0) and current_pos < 0:
            close_size = abs(current_pos)
            intents.append(
                self.create_intent(
                    symbol=event.symbol,
                    direction=1,  # Buy to close short perp
                    target_size=round(close_size, 4),
                    urgency=ExecutionUrgency.NORMAL,
                    limit_price=event.mark_price,
                    stop_price=None,
                    target_price=None,
                    reason=f"Funding carry exit: APR compressed to {annualized_apr*100:.2f}%",
                )
            )

        return intents

    def on_candle(self, event: CandleEvent) -> List[OrderIntent]:
        return []
