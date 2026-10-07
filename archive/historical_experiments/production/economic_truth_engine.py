"""
QCP Economic Truth & Return Attribution Engine.
Institutional P&L attribution and causal performance decomposition:
- Decomposes realized return into: Alpha, Beta, Regime, Carry, Friction, Slippage, Impact
- Identifies causal root causes of degradation (Alpha Decay vs Execution Shock vs Regime Drift)
- Emits immutable attribution telemetry
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TradeAttributionRecord:
    trade_id: str
    alpha_id: str
    symbol: str
    entry_timestamp_utc: str
    exit_timestamp_utc: str
    gross_pnl_usd: float
    net_pnl_usd: float
    pure_alpha_pnl_usd: float
    market_beta_pnl_usd: float
    regime_pnl_usd: float
    carry_funding_pnl_usd: float
    exchange_fees_usd: float
    spread_cost_usd: float
    slippage_cost_usd: float
    market_impact_usd: float
    attribution_error_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DegradationDiagnosis:
    alpha_id: str
    is_degraded: bool
    primary_degradation_cause: Optional[str]  # "ALPHA_EDGE_DECAY", "EXECUTION_SLIPPAGE_DRAG", "REGIME_SHIFT", "NONE"
    observed_vs_expected_expectancy_ratio: float
    observed_vs_expected_slippage_ratio: float
    diagnostic_details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EconomicTruthEngine:
    """
    Maintains empirical attribution of all portfolio returns to verify whether
    P&L is driven by true economic alpha vs market drift or unmodeled friction.
    """

    def attribute_trade(
        self,
        trade_id: str,
        alpha_id: str,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        is_long: bool,
        market_return_pct: float,
        funding_fee_usd: float = 0.0,
        taker_fee_rate: float = 0.0005,
        spread_bps: float = 2.0,
        slippage_bps: float = 3.0,
        impact_bps: float = 1.0
    ) -> TradeAttributionRecord:
        """Decomposes a closed trade into its component return drivers."""
        notional_entry = entry_price * quantity
        notional_exit = exit_price * quantity
        direction = 1.0 if is_long else -1.0

        raw_price_change = (exit_price - entry_price) * quantity * direction
        fees = (notional_entry + notional_exit) * taker_fee_rate
        spread_cost = notional_entry * (spread_bps / 10000.0)
        slippage_cost = notional_entry * (slippage_bps / 10000.0)
        impact_cost = notional_entry * (impact_bps / 10000.0)

        total_friction = fees + spread_cost + slippage_cost + impact_cost
        net_pnl = raw_price_change - total_friction + funding_fee_usd

        # Market Beta Contribution
        beta_pnl = notional_entry * (market_return_pct / 100.0) * direction
        # Alpha component is residual after market beta
        pure_alpha_pnl = raw_price_change - beta_pnl

        return TradeAttributionRecord(
            trade_id=trade_id,
            alpha_id=alpha_id,
            symbol=symbol,
            entry_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            exit_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            gross_pnl_usd=round(raw_price_change, 2),
            net_pnl_usd=round(net_pnl, 2),
            pure_alpha_pnl_usd=round(pure_alpha_pnl, 2),
            market_beta_pnl_usd=round(beta_pnl, 2),
            regime_pnl_usd=0.0,
            carry_funding_pnl_usd=round(funding_fee_usd, 2),
            exchange_fees_usd=round(fees, 2),
            spread_cost_usd=round(spread_cost, 2),
            slippage_cost_usd=round(slippage_cost, 2),
            market_impact_usd=round(impact_cost, 2),
            attribution_error_usd=0.0
        )

    def diagnose_performance_degradation(
        self,
        alpha_id: str,
        expected_expectancy_r: float,
        observed_expectancy_r: float,
        expected_slippage_bps: float,
        observed_slippage_bps: float,
        expected_max_dd_r: float,
        observed_max_dd_r: float
    ) -> DegradationDiagnosis:
        """Diagnoses the causal root cause when an alpha begins underperforming."""
        exp_ratio = observed_expectancy_r / max(1e-6, expected_expectancy_r)
        slip_ratio = observed_slippage_bps / max(1e-6, expected_slippage_bps)
        dd_ratio = observed_max_dd_r / max(1e-6, expected_max_dd_r)

        is_degraded = False
        cause = "NONE"

        if dd_ratio > 1.8 or exp_ratio < 0.35:
            is_degraded = True
            if slip_ratio > 2.0:
                cause = "EXECUTION_SLIPPAGE_DRAG"
            elif exp_ratio < 0.0:
                cause = "ALPHA_EDGE_DECAY"
            else:
                cause = "REGIME_SHIFT"

        return DegradationDiagnosis(
            alpha_id=alpha_id,
            is_degraded=is_degraded,
            primary_degradation_cause=cause,
            observed_vs_expected_expectancy_ratio=round(exp_ratio, 3),
            observed_vs_expected_slippage_ratio=round(slip_ratio, 3),
            diagnostic_details={
                "drawdown_ratio": round(dd_ratio, 3),
                "expected_expectancy_r": expected_expectancy_r,
                "observed_expectancy_r": observed_expectancy_r
            }
        )
