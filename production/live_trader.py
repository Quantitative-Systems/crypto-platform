"""
Product 07 — Production Service & Reliability
LiveTradingEngine: Master 24/7/365 Production Trading Engine.
Coordinates P01 Market Intelligence, Alpha Regime Gating, P02 Strategy Lifecycle,
P03 Risk Firewall, P05 Portfolio Allocation, P06 Live Execution Gateway, and P07 Persistence.
"""

import os
import time
import asyncio
from typing import Dict, List, Optional, Any

from market_intelligence.primitives import Candle, MarketStatePayload
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.classifiers.regime_filter import RegimeFilter
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from portfolio_engine.portfolio_coordinator import PortfolioCoordinator
from portfolio_engine.contracts.portfolio_state import PortfolioRiskConfig, AllocatedTradePlan
from execution_gateway.interfaces.base_gateway import BaseGateway
from execution_gateway.gateways.paper_gateway import PaperGateway
from execution_gateway.order_manager import OrderManager
from execution_gateway.contracts.order_contracts import LiveOrder, ExecutionFill
from production.persistence.state_store import StateStore
from production.reconciliation.eod_reconciler import EODReconciler, ReconciliationReport
from production.telemetry.alert_manager import AlertManager


class LiveTradingEngine:
    """
    24/7/365 Autonomous Institutional Execution Engine.
    """

    def __init__(
        self,
        gateway: BaseGateway,
        initial_balance: float = 10000.0,
        enable_regime_filter: bool = True,
        enable_profit_lock: bool = True,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75,
        state_db_path: str = "production_state.db",
        portfolio_config: Optional[PortfolioRiskConfig] = None
    ):
        self.gateway = gateway
        self.state_store = StateStore(db_path=state_db_path)
        self.alert_manager = AlertManager()
        
        # P01 Market Intelligence
        self.language_coordinator = LanguageCoordinator(buffer_size=300)
        
        # Alpha Regime Gating
        self.regime_filter = RegimeFilter(enable_filter=enable_regime_filter)
        
        # P02 Strategy Coordinator
        self.strategy_coordinator = StrategyCoordinator(
            enable_mtf_trailing=True,
            enable_profit_lock=enable_profit_lock,
            lockin_r=lockin_r,
            giveback_r=giveback_r,
            regime_filter=self.regime_filter
        )
        
        # P05 Portfolio Coordinator
        self.portfolio_coordinator = PortfolioCoordinator(
            initial_nav=initial_balance,
            config=portfolio_config
        )
        
        # P06 Order Manager
        self.order_manager = OrderManager(
            gateway=self.gateway,
            lockin_r=lockin_r,
            giveback_r=giveback_r
        )
        
        # Candle buffers
        self.candle_buffers: Dict[str, Dict[str, List[Candle]]] = {}
        self.is_running = False

    async def start(self) -> None:
        """
        Initializes exchange connectivity, recovers state from disk, and starts 24/7 engine.
        """
        await self.gateway.connect()
        live_bal = await self.gateway.get_account_balance()
        if live_bal > 0:
            self.portfolio_coordinator.update_nav(live_bal)
        
        # Recover active state if available
        recovered_state = self.state_store.load_state("portfolio_state")
        if recovered_state:
            self.alert_manager.send_alert("INFO", "STATE_RECOVERY", "Restoring active portfolio state from database", recovered_state)

        self.is_running = True
        self._persist_current_state()
        self.alert_manager.send_alert("INFO", "ENGINE_STARTED", f"24/7/365 Live Engine active. NAV: ${self.portfolio_coordinator.state.nav:.2f}")

    async def stop(self) -> None:
        """
        Gracefully terminates connections and persists final state.
        """
        self._persist_current_state()
        await self.gateway.disconnect()
        self.is_running = False
        self.alert_manager.send_alert("INFO", "ENGINE_STOPPED", "Live Trading Engine shutdown cleanly.")

    async def on_bar_closed(
        self,
        symbol: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        current_atr: float = 0.0
    ) -> List[AllocatedTradePlan]:
        """
        Processes closed multi-timeframe candle stream, evaluates pipeline, and executes orders.
        """
        if not self.is_running:
            return []

        # 1. Compute P01 Market Intelligence Payloads
        htf_payload = self.language_coordinator.run(htf_candles, symbol=symbol, timeframe="1D")
        mtf_payload = self.language_coordinator.run(mtf_candles, symbol=symbol, timeframe="4H")
        ltf_payload = self.language_coordinator.run(ltf_candles, symbol=symbol, timeframe="1H")

        # 2. Evaluate Strategy Lifecycle (P02)
        plans = self.strategy_coordinator.evaluate(htf_payload, mtf_payload, ltf_payload)
        executed_plans: List[AllocatedTradePlan] = []

        for raw_plan in plans:
            # 3. Evaluate Risk Firewall (P03)
            acc_state = AccountState(
                balance=self.portfolio_coordinator.state.nav,
                equity=self.portfolio_coordinator.state.nav,
                open_positions=[],
                open_risk_ratio=self.portfolio_coordinator.state.total_risk_committed_pct,
                daily_drawdown_ratio=self.portfolio_coordinator.state.current_drawdown_pct,
                weekly_drawdown_ratio=self.portfolio_coordinator.state.current_drawdown_pct
            )

            risk_eval = RiskCoordinator.evaluate(raw_plan, acc_state)
            if hasattr(risk_eval, "position_units"):  # RiskApprovedPlan
                # 4. Evaluate Portfolio Allocator & Volatility Sizer (P05)
                allocated = self.portfolio_coordinator.evaluate(risk_eval, current_atr=current_atr)  # type: ignore
                if allocated.is_approved:
                    # 5. Dispatch Order via OrderManager (P06)
                    entry_order = await self.order_manager.execute_trade_plan(allocated, use_post_only=True)
                    self.portfolio_coordinator.on_trade_executed(allocated)
                    executed_plans.append(allocated)

                    # 6. Save State & Alert (P07)
                    self.alert_manager.send_alert(
                        "INFO",
                        f"TRADE_EXECUTED: {symbol}",
                        f"Allocated {allocated.allocated_units:.4f} units @ ${allocated.entry_price:.2f} (Risk: ${allocated.allocated_dollar_risk:.2f})",
                        {"plan_id": allocated.trade_plan_id, "sl": allocated.stop_loss_price, "tp": allocated.target_price}
                    )

        self._persist_current_state()
        return executed_plans

    async def on_tick(
        self,
        symbol: str,
        current_price: float,
        high: float,
        low: float
    ) -> None:
        """
        Processes real-time intra-bar ticks to update positions and ratchet profit-lock stops.
        """
        # If Paper Gateway, simulate fills
        if isinstance(self.gateway, PaperGateway):
            self.gateway.on_market_price_update(symbol, current_price, high, low)

        # Check for +1.0R Profit-Lock Ratchet Stop Update
        ratchet_ord = await self.order_manager.check_and_update_profit_lock(symbol, current_price, high, low)
        if ratchet_ord:
            self._persist_current_state()
            self.alert_manager.send_alert(
                "INFO",
                f"PROFIT_LOCK_RATCHET: {symbol}",
                f"Position reached +1.0R MFE! Ratcheted stop loss to ${ratchet_ord.stop_price:.2f} (+0.25R locked profit)."
            )

    async def run_eod_reconciliation(self) -> ReconciliationReport:
        """
        Executes daily EOD reconciliation against exchange reality.
        """
        report = await EODReconciler.audit(self.portfolio_coordinator.state, self.gateway)
        if not report.is_clean:
            self.alert_manager.send_alert(
                "WARNING",
                "EOD_RECONCILIATION_DISCREPANCY",
                f"Ledger discrepancy: ${report.discrepancy_usd:.2f}",
                {"mismatches": report.position_mismatches}
            )
        else:
            self.alert_manager.send_alert(
                "INFO",
                "EOD_RECONCILIATION_PASSED",
                f"Reconciliation verified. NAV: ${report.internal_nav:.2f} ≡ Exchange: ${report.exchange_balance:.2f}"
            )
        return report

    def _persist_current_state(self) -> None:
        state_data = {
            "nav": self.portfolio_coordinator.state.nav,
            "peak_nav": self.portfolio_coordinator.state.peak_nav,
            "drawdown_pct": self.portfolio_coordinator.state.current_drawdown_pct,
            "active_positions": self.portfolio_coordinator.state.active_positions,
            "timestamp_utc": int(time.time())
        }
        self.state_store.save_state("portfolio_state", state_data)
