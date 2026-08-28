"""
Product 05 — Portfolio & Dynamic Risk Engine
Volatility-Targeted Position Sizing Module.
Dynamically scales position risk inversely with realized market volatility.
"""

import math
from typing import Tuple
from portfolio_engine.contracts.portfolio_state import PortfolioRiskConfig, PortfolioState
from risk_engine.contracts.risk_plan import RiskApprovedPlan


class VolatilityTargetSizer:
    """
    Computes volatility-scaled position sizing to maintain steady portfolio Value-at-Risk (VaR).
    """

    @staticmethod
    def calculate(
        plan: RiskApprovedPlan,
        portfolio_state: PortfolioState,
        config: PortfolioRiskConfig,
        current_atr: float = 0.0
    ) -> Tuple[float, float, float]:
        """
        Calculates volatility-scaled risk fraction, dollar risk, and allocated units.
        Returns: (allocated_units, dollar_risk, vol_scale_factor)
        """
        stop_dist = abs(plan.entry_price - plan.stop_loss_price)
        if stop_dist <= 0 or plan.entry_price <= 0 or portfolio_state.nav <= 0:
            return 0.0, 0.0, 1.0

        # Estimate annualized realized volatility from ATR or stop distance
        if current_atr > 0:
            daily_vol = current_atr / plan.entry_price
            realized_annual_vol = daily_vol * math.sqrt(365)
        else:
            # Fallback based on structural stop width
            stop_dist_pct = stop_dist / plan.entry_price
            realized_annual_vol = max(0.20, stop_dist_pct * math.sqrt(365))

        # Clamp realized volatility to realistic bounds
        realized_annual_vol = max(0.15, min(1.50, realized_annual_vol))

        # Volatility scale factor: target / realized
        target_vol = config.target_annual_volatility
        raw_vol_scale = target_vol / realized_annual_vol
        vol_scale = max(0.50, min(1.50, raw_vol_scale))

        # Scaled risk fraction
        scaled_risk_pct = config.max_risk_per_trade_pct * vol_scale
        scaled_risk_pct = max(config.min_risk_per_trade_pct, min(config.max_risk_per_trade_pct, scaled_risk_pct))

        dollar_risk = portfolio_state.nav * scaled_risk_pct
        allocated_units = dollar_risk / stop_dist

        return allocated_units, dollar_risk, vol_scale
