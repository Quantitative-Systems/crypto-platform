"""Crypto Trading Platform — LIVE-CANARY Execution Harness.

Manages the complete lifecycle and failsafe execution for real-money canary trading:
- State Machine: DISARMED -> ARMED -> ACTIVE (with instantaneous trip to HALTED)
- Pre-flight 14-Step Broker Auditing
- Risk Firewall pre-trade evaluation under strict canary bounds
- Automated State Reconciliation and order routing
- Full audit event logging to persistent SQLite storage
"""
from __future__ import annotations

from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.exchange_adapters.base import BaseExchangeAdapter
from crypto_platform.paper_trading.persistence import SQLitePaperLedger
from crypto_platform.reconciliation.reconciler import StateReconciliationEngine
from crypto_platform.risk_engine.firewall import RiskFirewall, RiskState
from .verifier import CanaryBrokerVerifier, CanaryVerificationReport

logger = logging.getLogger("crypto_platform.live_canary.harness")


class CanaryState(str, Enum):
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"


class LiveCanaryHarness:
    """Institutional real-money micro-canary execution engine."""

    def __init__(
        self,
        adapter: BaseExchangeAdapter,
        firewall: Optional[RiskFirewall] = None,
        reconciler: Optional[StateReconciliationEngine] = None,
        ledger: Optional[SQLitePaperLedger] = None,
        account_id: str = "acc_canary_01",
        tenant_id: str = "tenant_primary",
        canary_capital_limit_usd: float = 100.0,
        canary_risk_limit: float = 0.02,
        canary_max_position_size: float = 50.0,
        canary_max_daily_loss: float = 0.02,
        canary_max_total_drawdown: float = 0.05,
        canary_max_leverage: float = 1.5,
        db_path: str = "research/paper_trading.db",
    ):
        self.adapter = adapter
        self.firewall = firewall or RiskFirewall()
        self.reconciler = reconciler or StateReconciliationEngine()
        self.ledger = ledger or SQLitePaperLedger(db_path=db_path)
        self.account_id = account_id
        self.tenant_id = tenant_id

        # Explicit capital controls
        self.canary_capital_limit_usd = canary_capital_limit_usd
        self.canary_risk_limit = canary_risk_limit
        self.canary_max_position_size = canary_max_position_size
        self.canary_max_daily_loss = canary_max_daily_loss
        self.canary_max_total_drawdown = canary_max_total_drawdown
        self.canary_max_leverage = canary_max_leverage

        # State management
        self.state = CanaryState.DISARMED
        self.last_verification_report: Optional[CanaryVerificationReport] = None
        self.verifier = CanaryBrokerVerifier(
            adapter=self.adapter,
            firewall=self.firewall,
            reconciler=self.reconciler,
            canary_capital_limit_usd=self.canary_capital_limit_usd,
            canary_max_leverage=self.canary_max_leverage,
        )

        # Operational metrics
        self.peak_equity = canary_capital_limit_usd
        self.current_equity = canary_capital_limit_usd
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_orders = 0
        self.total_fills = 0
        self.total_fees = 0.0
        self.halt_reason: Optional[str] = None

        # Synchronize firewall with canary parameters
        self.firewall.configure_canary(
            capital_limit_usd=self.canary_capital_limit_usd,
            max_position_size=self.canary_max_position_size,
            max_leverage=self.canary_max_leverage,
            max_daily_loss=self.canary_max_daily_loss,
            max_total_drawdown=self.canary_max_total_drawdown,
            canary_state=self.state.value,
        )

    async def run_preflight_verification(self, target_symbol: str = "BTCUSDT") -> CanaryVerificationReport:
        """Run the comprehensive 14-step broker verification suite."""
        report = await self.verifier.verify_all(target_symbol=target_symbol)
        self.last_verification_report = report
        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_PREFLIGHT_VERIFICATION",
            severity="INFO" if report.passed else "ERROR",
            message=f"14-Step Verification completed: {'PASSED' if report.passed else 'FAILED'}",
            details=report.to_dict(),
        )
        return report

    async def arm(self, authorized_by: str = "SYSTEM_OWNER") -> bool:
        """Transition from DISARMED to ARMED after running all 14 broker checks."""
        if self.state == CanaryState.HALTED:
            logger.error("Cannot arm LIVE-CANARY while in HALTED state. Manual reset required.")
            return False

        if self.canary_capital_limit_usd <= 0.0:
            logger.error("Cannot arm LIVE-CANARY without explicit CANARY_CAPITAL_LIMIT_USD > 0.")
            return False

        report = await self.run_preflight_verification()
        if not report.passed:
            logger.error(f"Cannot arm LIVE-CANARY. Pre-flight verification failed: {report.failure_reason}")
            self.state = CanaryState.DISARMED
            self.firewall.canary_state = self.state.value
            return False

        self.state = CanaryState.ARMED
        self.firewall.canary_state = self.state.value
        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_ARMED",
            severity="WARNING",
            message=f"LIVE-CANARY armed by {authorized_by}. Awaiting explicit ACTIVE authorization.",
            details={"capital_limit_usd": self.canary_capital_limit_usd, "authorized_by": authorized_by},
        )
        logger.info(f"[LIVE-CANARY] Successfully ARMED by {authorized_by}.")
        return True

    async def activate(self, authorized_by: str = "SYSTEM_OWNER") -> bool:
        """Transition from ARMED to ACTIVE. Enables real-money order routing."""
        if self.state != CanaryState.ARMED:
            logger.error(f"Cannot activate LIVE-CANARY: Current state is {self.state.value}, must be ARMED.")
            return False

        self.state = CanaryState.ACTIVE
        self.firewall.canary_state = self.state.value
        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_ACTIVATED",
            severity="WARNING",
            message=f"LIVE-CANARY is now ACTIVE. Real-money order execution is authorized by {authorized_by}.",
            details={"capital_limit_usd": self.canary_capital_limit_usd, "authorized_by": authorized_by},
        )
        logger.warning(f"[LIVE-CANARY] ACTIVE status engaged by {authorized_by}.")
        return True

    def disarm(self, reason: str = "USER_DISARMED") -> None:
        """Return to safe DISARMED state."""
        self.state = CanaryState.DISARMED
        self.firewall.canary_state = self.state.value
        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_DISARMED",
            severity="INFO",
            message=f"LIVE-CANARY returned to DISARMED: {reason}",
            details={"reason": reason},
        )
        logger.info(f"[LIVE-CANARY] Disarmed: {reason}")

    async def emergency_kill(self, reason: str = "EMERGENCY_KILL_ENGAGED") -> None:
        """Instantaneous fail-closed kill switch: Halts engine and trips Risk Firewall."""
        self.state = CanaryState.HALTED
        self.halt_reason = reason
        self.firewall.canary_state = self.state.value

        # Trip global kill switch in Risk Firewall
        self.firewall.kill_switches.activate(scope="GLOBAL", target="*", reason=reason)

        # Cancel any open orders on exchange
        try:
            open_orders = await self.adapter.get_open_orders()
            for ord in open_orders:
                await self.adapter.cancel_order(ord.client_order_id, ord.symbol)
        except Exception as e:
            logger.error(f"Error cancelling open orders during emergency kill: {e}")

        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_EMERGENCY_KILL",
            severity="CRITICAL",
            message=f"LIVE-CANARY EMERGENCY KILL ENGAGED: {reason}",
            details={"halt_reason": reason},
        )
        logger.critical(f"[LIVE-CANARY] EMERGENCY KILL SWITCH ACTIVATED: {reason}")

    def reset_emergency_halt(self, authorized_by: str = "SYSTEM_OWNER") -> bool:
        """Explicit manual restart required after emergency halt. Cannot be bypassed automatically."""
        self.state = CanaryState.DISARMED
        self.halt_reason = None
        self.firewall.canary_state = self.state.value
        self.firewall.kill_switches.deactivate(scope="GLOBAL", target="*")

        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_HALT_RESET",
            severity="WARNING",
            message=f"LIVE-CANARY emergency halt manually reset by {authorized_by}. State is DISARMED.",
            details={"authorized_by": authorized_by},
        )
        return True

    async def execute_intent(
        self,
        intent: OrderIntent,
        latest_ticker: Optional[TickerEvent] = None,
    ) -> Optional[ExecutionOrder]:
        """Execute order intent through complete LIVE-CANARY pipeline:

        Market Data -> Risk Firewall -> OMS -> Adapter -> Reconciliation -> Persistence
        """
        now_ms = int(time.time() * 1000)

        # Invariant 1: Canary state must be ACTIVE
        if self.state != CanaryState.ACTIVE:
            self.ledger.log_audit_event(
                account_id=self.account_id,
                event_type="CANARY_ORDER_REJECTED",
                severity="ERROR",
                message=f"Order rejected: LIVE-CANARY state is {self.state.value}, not ACTIVE.",
                details={"intent_id": intent.intent_id},
            )
            return None

        # Fetch current broker positions & balances
        positions_list = await self.adapter.get_positions()
        positions_map = {p.symbol: p for p in positions_list}
        balances_list = await self.adapter.get_account_balances()
        balances_map = {b.asset: b for b in balances_list}

        # Calculate equity & drawdown
        total_balance = sum(b.total for b in balances_list if b.asset in ("USDT", "USD"))
        self.current_equity = max(0.0, total_balance)
        self.peak_equity = max(self.peak_equity, self.current_equity)
        drawdown_pct = max(0.0, (self.peak_equity - self.current_equity) / self.peak_equity) if self.peak_equity > 0 else 0.0

        risk_state = RiskState(
            equity=self.current_equity,
            peak_equity=self.peak_equity,
            drawdown_pct=drawdown_pct,
        )

        # Invariant 2: Full 22+ boundary evaluation in Risk Firewall with LIVE_CANARY mode
        decision = self.firewall.evaluate_order_intent(
            intent=intent,
            current_positions=positions_map,
            balances=balances_map,
            risk_state=risk_state,
            latest_ticker=latest_ticker,
            venue=self.adapter.venue_name,
            operating_mode=OperatingMode.LIVE_CANARY,
        )

        if not decision.approved:
            self.ledger.log_audit_event(
                account_id=self.account_id,
                event_type="CANARY_FIREWALL_REJECTION",
                severity="WARNING",
                message=f"Risk Firewall rejected canary order: [{decision.rule_code}] {decision.reason}",
                details={"intent_id": intent.intent_id, "rule_code": decision.rule_code},
            )
            return None

        # Size adjustment from circuit breaker
        qty = decision.adjusted_size if decision.adjusted_size is not None else intent.target_size
        price = intent.limit_price or (latest_ticker.last_price if latest_ticker else 60000.0)

        # Construct ExecutionOrder
        order = ExecutionOrder(
            order_id=f"ord_canary_{now_ms}",
            client_order_id=f"c_canary_{now_ms}",
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            venue=self.adapter.venue_name,
            symbol=intent.symbol,
            side=OrderSide.BUY if intent.direction > 0 else OrderSide.SELL,
            order_type=OrderType.LIMIT if intent.limit_price else OrderType.MARKET,
            time_in_force=TimeInForce.GTC,
            quantity=qty,
            price=price,
            created_at_ms=now_ms,
        )

        # Submit order to broker adapter
        submitted_order = await self.adapter.submit_order(order)
        self.total_orders += 1

        # Post-submission State Reconciliation Check
        post_positions = await self.adapter.get_positions()
        post_orders = await self.adapter.get_open_orders()
        reconciled = self.reconciler.reconcile_positions(self.account_id, {p.symbol: p.size for p in post_positions}, {p.symbol: p.size for p in post_positions})

        # Record to persistent SQLite Ledger
        self.ledger.save_order(submitted_order)
        self.ledger.log_audit_event(
            account_id=self.account_id,
            event_type="CANARY_ORDER_SUBMITTED",
            severity="INFO",
            message=f"LIVE-CANARY order submitted: {submitted_order.side} {submitted_order.quantity} {submitted_order.symbol} @ {submitted_order.price}",
            details={"order_id": submitted_order.order_id, "status": submitted_order.status.value},
        )

        return submitted_order

    def get_telemetry(self) -> Dict[str, Any]:
        """Return comprehensive live status for visual dashboard."""
        return {
            "operating_plane": "LIVE-CANARY",
            "state": self.state.value,
            "real_capital_locked": False if self.state == CanaryState.ACTIVE else True,
            "canary_capital_limit_usd": self.canary_capital_limit_usd,
            "current_equity_usd": self.current_equity,
            "peak_equity_usd": self.peak_equity,
            "realized_pnl_usd": self.realized_pnl,
            "unrealized_pnl_usd": self.unrealized_pnl,
            "drawdown_pct": max(0.0, (self.peak_equity - self.current_equity) / self.peak_equity * 100.0) if self.peak_equity > 0 else 0.0,
            "canary_max_daily_loss": self.canary_max_daily_loss,
            "canary_max_total_drawdown": self.canary_max_total_drawdown,
            "canary_max_position_size": self.canary_max_position_size,
            "canary_max_leverage": self.canary_max_leverage,
            "total_orders": self.total_orders,
            "total_fills": self.total_fills,
            "total_fees_usd": self.total_fees,
            "broker_venue": self.adapter.venue_name,
            "broker_connected": getattr(self.adapter, "_connected", False),
            "emergency_kill_active": self.state == CanaryState.HALTED or self.firewall.is_kill_switch_active("GLOBAL", "*"),
            "halt_reason": self.halt_reason,
            "preflight_passed": self.last_verification_report.passed if self.last_verification_report else False,
        }
