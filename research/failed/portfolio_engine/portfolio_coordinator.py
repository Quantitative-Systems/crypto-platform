"""
Product 05 — Portfolio & Dynamic Risk Engine
Portfolio Coordinator: Master multi-asset risk allocator, volatility sizer, and heat ceiling governor.
"""

from typing import Optional, Dict
from portfolio_engine.contracts.portfolio_state import (
    PortfolioRiskConfig,
    PortfolioState,
    AssetExposure,
    AllocatedTradePlan
)
from portfolio_engine.allocator.volatility_target_sizer import VolatilityTargetSizer
from portfolio_engine.allocator.drawdown_dampener import DrawdownDampener
from risk_engine.contracts.risk_plan import RiskApprovedPlan


class PortfolioCoordinator:
    """
    Coordinates multi-asset portfolio heat, volatility-targeted sizing, and drawdown protection.
    """

    def __init__(
        self,
        initial_nav: float = 10000.0,
        config: Optional[PortfolioRiskConfig] = None
    ):
        self.config = config or PortfolioRiskConfig()
        self.state = PortfolioState(
            nav=initial_nav,
            cash_balance=initial_nav,
            peak_nav=initial_nav
        )

    def evaluate(
        self,
        plan: RiskApprovedPlan,
        current_atr: float = 0.0
    ) -> AllocatedTradePlan:
        """
        Evaluates a RiskApprovedPlan from P03 against portfolio-wide constraints and sizes it.
        """
        self.state.update_drawdown()
        self.state.recalculate_exposures()

        symbol = plan.symbol

        # 1. Max Concurrent Positions Check
        if len(self.state.active_positions) >= self.config.max_concurrent_trades:
            return self._reject(plan, f"REJECT_PORTFOLIO_MAX_CONCURRENT_TRADES_{self.config.max_concurrent_trades}")

        # 2. Drawdown Dampener Evaluation
        dampener_factor, dd_rejection = DrawdownDampener.get_dampener_factor(self.state, self.config)
        if dd_rejection:
            return self._reject(plan, dd_rejection)

        # 3. Volatility-Targeted Position Sizing
        base_units, base_dollar_risk, vol_scale = VolatilityTargetSizer.calculate(
            plan, self.state, self.config, current_atr=current_atr
        )

        final_dollar_risk = base_dollar_risk * dampener_factor
        final_units = base_units * dampener_factor
        final_risk_fraction = (final_dollar_risk / self.state.nav) if self.state.nav > 0 else 0.0

        if final_units <= 0:
            return self._reject(plan, "REJECT_PORTFOLIO_ZERO_ALLOCATION")

        # 4. Single Asset Concentration Limit
        asset_exp = self.state.asset_exposures.get(symbol, AssetExposure(symbol=symbol))
        new_asset_risk = asset_exp.total_dollar_risk + final_dollar_risk
        max_allowed_asset_risk = self.state.nav * self.config.max_asset_concentration_pct

        if new_asset_risk > max_allowed_asset_risk:
            return self._reject(plan, f"REJECT_PORTFOLIO_ASSET_CONCENTRATION_{symbol}")

        # 5. Total Portfolio Heat Ceiling
        new_portfolio_risk = self.state.total_risk_committed_usd + final_dollar_risk
        max_allowed_portfolio_risk = self.state.nav * self.config.max_total_portfolio_risk_pct

        if new_portfolio_risk > max_allowed_portfolio_risk:
            return self._reject(plan, "REJECT_PORTFOLIO_TOTAL_HEAT_CEILING")

        # Approval
        return AllocatedTradePlan(
            trade_plan_id=plan.trade_plan_id,
            hypothesis_id=plan.hypothesis_id,
            symbol=symbol,
            entry_price=plan.entry_price,
            stop_loss_price=plan.stop_loss_price,
            target_price=plan.target_price,
            allocated_units=final_units,
            allocated_dollar_risk=final_dollar_risk,
            risk_fraction=final_risk_fraction,
            volatility_scale_factor=vol_scale,
            drawdown_dampener_factor=dampener_factor,
            is_approved=True,
            rejection_reason=None
        )

    def on_trade_executed(self, plan: AllocatedTradePlan) -> None:
        """
        Updates internal portfolio state upon trade fill.
        """
        symbol = plan.symbol
        self.state.active_positions[plan.trade_plan_id] = {
            "symbol": symbol,
            "units": plan.allocated_units,
            "entry_price": plan.entry_price,
            "stop_loss_price": plan.stop_loss_price,
            "dollar_risk": plan.allocated_dollar_risk
        }

        if symbol not in self.state.asset_exposures:
            self.state.asset_exposures[symbol] = AssetExposure(symbol=symbol)

        exp = self.state.asset_exposures[symbol]
        exp.active_trades_count += 1
        exp.total_dollar_risk += plan.allocated_dollar_risk
        exp.total_notional += plan.allocated_units * plan.entry_price

        self.state.recalculate_exposures()

    def on_trade_closed(self, trade_plan_id: str, pnl_usd: float) -> None:
        """
        Updates internal portfolio state upon trade exit.
        """
        if trade_plan_id in self.state.active_positions:
            pos = self.state.active_positions.pop(trade_plan_id)
            symbol = pos["symbol"]
            dollar_risk = pos["dollar_risk"]
            notional = pos["units"] * pos["entry_price"]

            if symbol in self.state.asset_exposures:
                exp = self.state.asset_exposures[symbol]
                exp.active_trades_count = max(0, exp.active_trades_count - 1)
                exp.total_dollar_risk = max(0.0, exp.total_dollar_risk - dollar_risk)
                exp.total_notional = max(0.0, exp.total_notional - notional)

            self.state.nav += pnl_usd
            self.state.cash_balance += pnl_usd
            self.state.update_drawdown()
            self.state.recalculate_exposures()

    def update_nav(self, current_nav: float) -> None:
        """
        Synchronizes portfolio NAV with external live exchange balance.
        """
        self.state.nav = current_nav
        self.state.cash_balance = current_nav
        self.state.update_drawdown()
        self.state.recalculate_exposures()

    def _reject(self, plan: RiskApprovedPlan, reason: str) -> AllocatedTradePlan:
        return AllocatedTradePlan(
            trade_plan_id=plan.trade_plan_id,
            hypothesis_id=plan.hypothesis_id,
            symbol=plan.symbol,
            entry_price=plan.entry_price,
            stop_loss_price=plan.stop_loss_price,
            target_price=plan.target_price,
            allocated_units=0.0,
            allocated_dollar_risk=0.0,
            risk_fraction=0.0,
            volatility_scale_factor=1.0,
            drawdown_dampener_factor=0.0,
            is_approved=False,
            rejection_reason=reason
        )
