"""
Quantitative Systems Platform (QSP) — Portfolio Hedging & Protection Engine (Family 9B).

Sits above the individual strategy layer to monitor net crypto beta, cross-asset
correlation, and portfolio heat. Triggers dynamically sized protective hedges or
exposure throttles during hostile regimes.
Enforces Capital Feasibility: Emits HEDGE_UNAVAILABLE if account size cannot
support exchange minimum notional constraints.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class HedgeAction(str, Enum):
    NO_HEDGE_NEEDED = "NO_HEDGE_NEEDED"
    HEDGE_ACTIVE = "HEDGE_ACTIVE"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    REJECT_NEW_TRADE = "REJECT_NEW_TRADE"
    HEDGE_UNAVAILABLE = "HEDGE_UNAVAILABLE"


@dataclass
class PositionExposure:
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    notional_usd: float
    risk_usd: float


@dataclass
class HedgingDecision:
    action: HedgeAction
    net_portfolio_beta: float
    total_portfolio_heat_pct: float
    recommended_hedge_symbol: str
    target_hedge_notional: float
    executable_hedge_notional: float
    min_exchange_notional: float
    reason: str


class PortfolioHedgingEngine:
    """
    Evaluates aggregate portfolio exposure and generates defensive hedging decisions.
    """

    # Empirical asset betas relative to BTC
    ASSET_BETAS = {
        "BTCUSDT": 1.00,
        "BTC/USDT": 1.00,
        "ETHUSDT": 1.15,
        "ETH/USDT": 1.15,
        "SOLUSDT": 1.45,
        "SOL/USDT": 1.45,
    }

    MIN_EXCHANGE_NOTIONAL = 5.00  # Binance USD-M Futures minimum notional

    def __init__(
        self,
        max_allowable_beta: float = 2.0,  # Max unhedged net beta
        max_portfolio_heat_pct: float = 3.0,  # Max concurrent risk 3.0%
        hedge_venue: str = "USDM_FUTURES",
    ):
        self.max_allowable_beta = max_allowable_beta
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.hedge_venue = hedge_venue

    def calculate_net_beta(self, open_positions: List[PositionExposure], account_equity: float) -> float:
        """Calculates total weighted net crypto beta across all open positions."""
        if account_equity <= 0:
            return 0.0
        total_beta = 0.0
        for pos in open_positions:
            beta = self.ASSET_BETAS.get(pos.symbol, 1.0)
            weight = pos.notional_usd / account_equity
            sign = 1.0 if pos.direction == "LONG" else -1.0
            total_beta += sign * weight * beta
        return total_beta

    def calculate_portfolio_heat(self, open_positions: List[PositionExposure], account_equity: float) -> float:
        """Calculates total percentage of equity currently risked."""
        if account_equity <= 0:
            return 0.0
        total_risk_usd = sum(pos.risk_usd for pos in open_positions)
        return (total_risk_usd / account_equity) * 100.0

    def evaluate_hedge_requirement(
        self,
        open_positions: List[PositionExposure],
        account_equity: float,
        macro_regime_is_hostile: bool = False,
    ) -> HedgingDecision:
        """
        Evaluates whether a portfolio hedge is required, executable, or unavailable.
        """
        net_beta = self.calculate_net_beta(open_positions, account_equity)
        heat_pct = self.calculate_portfolio_heat(open_positions, account_equity)

        # 1. Condition check: Is risk excessive?
        needs_hedge = False
        reason = "Portfolio risk metrics within safe limits"

        if heat_pct >= self.max_portfolio_heat_pct:
            needs_hedge = True
            reason = f"Portfolio heat ({heat_pct:.2f}%) exceeds safety ceiling ({self.max_portfolio_heat_pct:.2f}%)"
        elif net_beta > self.max_allowable_beta and macro_regime_is_hostile:
            needs_hedge = True
            reason = f"Net beta ({net_beta:.2f}) exceeds limit ({self.max_allowable_beta:.2f}) during hostile market regime"
        elif net_beta > (self.max_allowable_beta * 1.5):
            needs_hedge = True
            reason = f"Net beta ({net_beta:.2f}) severely elevated"

        if not needs_hedge:
            return HedgingDecision(
                action=HedgeAction.NO_HEDGE_NEEDED,
                net_portfolio_beta=round(net_beta, 2),
                total_portfolio_heat_pct=round(heat_pct, 2),
                recommended_hedge_symbol="BTCUSDT",
                target_hedge_notional=0.0,
                executable_hedge_notional=0.0,
                min_exchange_notional=self.MIN_EXCHANGE_NOTIONAL,
                reason=reason,
            )

        # 2. Sizing the hedge: Short BTC to bring net beta down to target (e.g. 1.0)
        target_beta_reduction = net_beta - 1.0
        # Notional required = reduction * equity / beta_btc
        target_hedge_notional = max(0.0, target_beta_reduction * account_equity)

        # 3. Capital Feasibility Check
        if target_hedge_notional < self.MIN_EXCHANGE_NOTIONAL:
            return HedgingDecision(
                action=HedgeAction.HEDGE_UNAVAILABLE,
                net_portfolio_beta=round(net_beta, 2),
                total_portfolio_heat_pct=round(heat_pct, 2),
                recommended_hedge_symbol="BTCUSDT",
                target_hedge_notional=round(target_hedge_notional, 2),
                executable_hedge_notional=0.0,
                min_exchange_notional=self.MIN_EXCHANGE_NOTIONAL,
                reason=(
                    f"Required hedge notional (${target_hedge_notional:.2f}) is below exchange minimum "
                    f"(${self.MIN_EXCHANGE_NOTIONAL:.2f}). Fallback: REDUCE_EXPOSURE or REJECT_NEW_TRADE."
                ),
            )

        # Round to executable lot
        # BTC price approx $45,000, step 0.001 BTC = $45
        # If target notional < 45, round up or down based on risk
        executable_notional = max(self.MIN_EXCHANGE_NOTIONAL, target_hedge_notional)

        return HedgingDecision(
            action=HedgeAction.HEDGE_ACTIVE,
            net_portfolio_beta=round(net_beta, 2),
            total_portfolio_heat_pct=round(heat_pct, 2),
            recommended_hedge_symbol="BTCUSDT",
            target_hedge_notional=round(target_hedge_notional, 2),
            executable_hedge_notional=round(executable_notional, 2),
            min_exchange_notional=self.MIN_EXCHANGE_NOTIONAL,
            reason=f"Active defensive short hedge triggered: {reason}",
        )
