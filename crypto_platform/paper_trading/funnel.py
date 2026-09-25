"""Crypto Trading Platform — Execution Funnel & Rejection Observability.

Tracks granular event conversion through the 14-stage execution funnel:
Market Data → Closed Candles → Strategy Evaluation → Signal → Order Intent →
Risk Firewall → Portfolio Allocation → OMS → Simulator → Resting → Fills.

Provides structured, machine-readable rejection reasons to identify
exact bottlenecks without modifying strategy parameters or manufacturing signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionFunnel:
    """Standardized institutional execution funnel telemetry."""

    market_events: int = 0
    unclosed_candles: int = 0
    duplicate_candles: int = 0
    closed_candles: int = 0
    strategy_evaluations: int = 0
    signals: int = 0
    order_intents: int = 0
    risk_rejections: int = 0
    allocation_rejections: int = 0
    oms_acceptances: int = 0
    simulator_submissions: int = 0
    resting_orders: int = 0
    expired_orders: int = 0
    cancelled_orders: int = 0
    partial_fills: int = 0
    full_fills: int = 0

    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    strategy_funnel: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def record_rejection(self, reason: str, count: int = 1) -> None:
        """Records a machine-readable rejection code."""
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + count

    def record_strategy_metric(self, strategy_id: str, metric: str, count: int = 1) -> None:
        """Records per-strategy conversion metrics."""
        strat_dict = self.strategy_funnel.setdefault(strategy_id, {})
        strat_dict[metric] = strat_dict.get(metric, 0) + count

    def to_dict(self) -> Dict[str, Any]:
        """Serializes funnel to dictionary for JSON persistence."""
        return {
            "market_events": self.market_events,
            "unclosed_candles": self.unclosed_candles,
            "duplicate_candles": self.duplicate_candles,
            "closed_candles": self.closed_candles,
            "strategy_evaluations": self.strategy_evaluations,
            "signals": self.signals,
            "order_intents": self.order_intents,
            "risk_accepted": self.order_intents - self.risk_rejections,
            "risk_rejections": self.risk_rejections,
            "allocation_rejections": self.allocation_rejections,
            "oms_acceptances": self.oms_acceptances,
            "simulator_submissions": self.simulator_submissions,
            "resting_orders": self.resting_orders,
            "expired_orders": self.expired_orders,
            "cancelled_orders": self.cancelled_orders,
            "partial_fills": self.partial_fills,
            "full_fills": self.full_fills,
            "total_fills": self.full_fills + self.partial_fills,
            "rejection_reasons": dict(sorted(self.rejection_reasons.items())),
            "by_strategy": {k: dict(v) for k, v in self.strategy_funnel.items()},
        }

    def format_ascii(self) -> str:
        """Returns clean text representation of the funnel."""
        lines = [
            f"Market events:          {self.market_events}",
            f"Closed candles:         {self.closed_candles}",
            f"Strategy evaluations:   {self.strategy_evaluations}",
            f"Signals:                {self.signals}",
            f"Order intents:          {self.order_intents}",
            f"Risk accepted:          {max(0, self.order_intents - self.risk_rejections)}",
            f"OMS accepted:           {self.oms_acceptances}",
            f"Simulator submitted:    {self.simulator_submissions}",
            f"Resting:                {self.resting_orders}",
            f"Expired:                {self.expired_orders}",
            f"Cancelled:              {self.cancelled_orders}",
            f"Partial fills:          {self.partial_fills}",
            f"Full fills:             {self.full_fills}",
        ]
        return "\n".join(lines)
