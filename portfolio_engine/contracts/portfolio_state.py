"""
Product 05 — Portfolio & Dynamic Risk Engine
Contracts for Portfolio State, Allocation Plans, and Portfolio Risk Configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass(frozen=True)
class PortfolioRiskConfig:
    """
    Institutional portfolio risk configuration parameters.
    """
    max_total_portfolio_risk_pct: float = 0.03    # Max 3.0% NAV total portfolio risk
    max_risk_per_trade_pct: float = 0.01          # Max 1.0% NAV risk per trade
    min_risk_per_trade_pct: float = 0.002         # Min 0.2% NAV risk floor
    max_asset_concentration_pct: float = 0.015    # Max 1.5% NAV risk per single asset
    target_annual_volatility: float = 0.40        # 40% annualized crypto vol target
    drawdown_tier_1_pct: float = 0.05             # 5.0% DD -> 50% risk scale
    drawdown_tier_2_pct: float = 0.10             # 10.0% DD -> 0% risk scale (Circuit Pause)
    max_concurrent_trades: int = 5                # Maximum simultaneous open positions


@dataclass
class AssetExposure:
    """
    Tracks active risk and notional exposure per asset.
    """
    symbol: str
    active_trades_count: int = 0
    total_dollar_risk: float = 0.0
    total_notional: float = 0.0


@dataclass
class PortfolioState:
    """
    Real-time multi-asset portfolio accounting and risk telemetry.
    """
    nav: float
    cash_balance: float
    peak_nav: float
    current_drawdown_pct: float = 0.0
    active_positions: Dict[str, Any] = field(default_factory=dict)
    asset_exposures: Dict[str, AssetExposure] = field(default_factory=dict)
    total_risk_committed_usd: float = 0.0
    total_risk_committed_pct: float = 0.0

    def update_drawdown(self) -> None:
        if self.nav > self.peak_nav:
            self.peak_nav = self.nav
        if self.peak_nav > 0:
            self.current_drawdown_pct = max(0.0, (self.peak_nav - self.nav) / self.peak_nav)
        else:
            self.current_drawdown_pct = 0.0

    def recalculate_exposures(self) -> None:
        tot_risk = sum(exp.total_dollar_risk for exp in self.asset_exposures.values())
        self.total_risk_committed_usd = tot_risk
        self.total_risk_committed_pct = (tot_risk / self.nav) if self.nav > 0 else 0.0


@dataclass(frozen=True)
class AllocatedTradePlan:
    """
    Execution-ready trade plan authorized and sized by Product 05 Portfolio Allocator.
    """
    trade_plan_id: str
    hypothesis_id: str
    symbol: str
    entry_price: float
    stop_loss_price: float
    target_price: float
    allocated_units: float
    allocated_dollar_risk: float
    risk_fraction: float
    volatility_scale_factor: float
    drawdown_dampener_factor: float
    is_approved: bool
    rejection_reason: Optional[str] = None
