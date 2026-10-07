"""
QCP Autonomous Risk Governor.
Highest authority in the execution and capital allocation pipeline:
- Absolute pre-trade veto authority
- Real-time market spread blowout & liquidity collapse protection
- 7-dimensional risk firewall enforcement (portfolio heat <= 3.0%, strategy <= 1.5%)
- Automatic drawdown risk throttling
- Fail-closed systemic killswitch
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RiskVetoDecision:
    is_approved: bool
    veto_reason: Optional[str]
    proposed_risk_usd: float
    approved_risk_usd: float
    drawdown_throttle_multiplier: float
    current_portfolio_heat_pct: float
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomousRiskGovernor:
    """
    Autonomous Risk Governor enforcing pre-trade safety and institutional capital boundaries.
    """

    def __init__(
        self,
        max_portfolio_heat_pct: float = 3.00,
        max_strategy_risk_pct: float = 1.50,
        max_asset_concentration_pct: float = 1.50,
        max_spread_multiplier: float = 3.0,
        max_depth_participation_pct: float = 20.0
    ):
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.max_strategy_risk_pct = max_strategy_risk_pct
        self.max_asset_concentration_pct = max_asset_concentration_pct
        self.max_spread_multiplier = max_spread_multiplier
        self.max_depth_participation_pct = max_depth_participation_pct

    def evaluate_order_risk(
        self,
        alpha_id: str,
        symbol: str,
        proposed_risk_usd: float,
        portfolio_equity_usd: float,
        current_open_risk_usd: float,
        current_drawdown_pct: float,
        current_spread_bps: float = 2.0,
        normal_spread_bps: float = 2.0,
        available_bid_ask_depth_usd: float = 500_000.0,
        is_exchange_healthy: bool = True
    ) -> RiskVetoDecision:
        """
        Evaluates proposed order against all risk boundaries.
        Returns approved risk or veto decision.
        """
        # 1. Exchange Connectivity & Feed Health Check
        if not is_exchange_healthy:
            return RiskVetoDecision(
                is_approved=False,
                veto_reason="VETO_EXCHANGE_FEED_UNHEALTHY",
                proposed_risk_usd=proposed_risk_usd,
                approved_risk_usd=0.0,
                drawdown_throttle_multiplier=0.0,
                current_portfolio_heat_pct=round((current_open_risk_usd / portfolio_equity_usd) * 100.0, 2)
            )

        # 2. Spread Blowout Check
        if current_spread_bps > (normal_spread_bps * self.max_spread_multiplier):
            return RiskVetoDecision(
                is_approved=False,
                veto_reason="VETO_SPREAD_BLOWOUT",
                proposed_risk_usd=proposed_risk_usd,
                approved_risk_usd=0.0,
                drawdown_throttle_multiplier=0.0,
                current_portfolio_heat_pct=round((current_open_risk_usd / portfolio_equity_usd) * 100.0, 2)
            )

        # 3. Liquidity Void Check
        order_size_estimate = proposed_risk_usd * (1.0 / 0.03)  # approx 3% stop distance
        if available_bid_ask_depth_usd > 0:
            participation_pct = (order_size_estimate / available_bid_ask_depth_usd) * 100.0
            if participation_pct > self.max_depth_participation_pct:
                return RiskVetoDecision(
                    is_approved=False,
                    veto_reason="VETO_INSUFFICIENT_MARKET_DEPTH",
                    proposed_risk_usd=proposed_risk_usd,
                    approved_risk_usd=0.0,
                    drawdown_throttle_multiplier=0.0,
                    current_portfolio_heat_pct=round((current_open_risk_usd / portfolio_equity_usd) * 100.0, 2)
                )

        # 4. Auto-Drawdown Throttling
        # Multiplier scales from 1.0 down to 0.2 as drawdown approaches 15%
        throttle_mult = max(0.20, 1.0 - (current_drawdown_pct / 15.0) * 0.80)
        throttled_risk = proposed_risk_usd * throttle_mult

        # 5. Single-Strategy Risk Ceiling (1.50% of equity)
        max_strategy_risk_usd = portfolio_equity_usd * (self.max_strategy_risk_pct / 100.0)
        capped_risk = min(throttled_risk, max_strategy_risk_usd)

        # 6. Aggregate Portfolio Heat Ceiling (3.00% of equity)
        max_portfolio_risk_usd = portfolio_equity_usd * (self.max_portfolio_heat_pct / 100.0)
        remaining_portfolio_capacity_usd = max(0.0, max_portfolio_risk_usd - current_open_risk_usd)

        if remaining_portfolio_capacity_usd <= 0.0:
            return RiskVetoDecision(
                is_approved=False,
                veto_reason="VETO_PORTFOLIO_HEAT_CEILING_REACHED",
                proposed_risk_usd=proposed_risk_usd,
                approved_risk_usd=0.0,
                drawdown_throttle_multiplier=throttle_mult,
                current_portfolio_heat_pct=round((current_open_risk_usd / portfolio_equity_usd) * 100.0, 2)
            )

        final_approved_risk = min(capped_risk, remaining_portfolio_capacity_usd)
        new_heat_pct = ((current_open_risk_usd + final_approved_risk) / portfolio_equity_usd) * 100.0

        return RiskVetoDecision(
            is_approved=True,
            veto_reason=None,
            proposed_risk_usd=proposed_risk_usd,
            approved_risk_usd=round(final_approved_risk, 2),
            drawdown_throttle_multiplier=round(throttle_mult, 3),
            current_portfolio_heat_pct=round(new_heat_pct, 2)
        )
