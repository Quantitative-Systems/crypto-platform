"""
QCP Phase 6 — Unified Risk Engine.
Implements the absolute risk gatekeeper of the Quantitative Crypto Platform.

Features:
1. Pre-trade Risk: order size sanity, price collars, notional limits.
2. Intraday Risk: loss velocity tracking, maximum daily drawdown.
3. Portfolio Risk: aggregate exposure, net delta, factor exposure.
4. Margin & Leverage Risk: maintenance margin buffer, gross leverage ceiling.
5. Liquidity Risk: order size vs order book depth, market impact limit.
6. Concentration & Correlation Risk: single-asset and directional cluster caps.
7. Drawdown Risk: tiered risk reduction and circuit-breaker shutdown.
8. Kill Switch & Emergency Halt: instant cancellation and position freeze.

VETO AUTHORITY:
The Risk Engine holds absolute veto authority over all trading orders, portfolio recommendations,
and hedging operations. Any veto is final and non-negotiable.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from platform_core.foundation.audit_logger import AuditLogger, AuditLevel
from platform_core.foundation.clock import SystemClock
from platform_core.foundation.error_taxonomy import PlatformError, ErrorCategory, ErrorSeverity
from risk_engine.portfolio_risk_firewall import (
    PortfolioRiskFirewall,
    FirewallDecision,
    FirewallAction,
    FirewallThresholds,
)

logger = logging.getLogger("QCP.RiskEngine")


class KillSwitchState(str, enum.Enum):
    ARMED_NORMAL = "ARMED_NORMAL"
    THROTTLED = "THROTTLED"
    EMERGENCY_HALT = "EMERGENCY_HALT"
    HARD_KILL = "HARD_KILL"


class RiskVetoError(PlatformError):
    """Raised when an operation violates risk constraints and is vetoed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.RISK,
            severity=ErrorSeverity.HIGH,
            details=details or {},
        )


@dataclass
class PreTradeOrderSpec:
    strategy_id: str
    symbol: str
    order_type: str
    direction: str  # BUY / SELL / LONG / SHORT
    quantity: float
    limit_price: Optional[float]
    notional_usd: float
    current_market_price: float
    stop_loss_price: Optional[float] = None
    account_equity_usd: float = 10_000.0


@dataclass
class AccountViabilityResult:
    """Economic viability audit for account and order scale (Directive EABG-001)."""
    is_viable: bool
    verdict: str  # "APPROVED" or "INSUFFICIENT CAPITAL / NO TRADE"
    account_equity_usd: float
    order_notional_usd: float
    estimated_risk_usd: float
    total_friction_usd: float
    friction_to_risk_ratio_pct: float
    rejection_reason: Optional[str] = None


@dataclass
class RiskCheckResult:
    approved: bool
    risk_action: FirewallAction
    allocated_quantity: float
    rejection_reasons: List[str]
    kill_switch_state: KillSwitchState
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UnifiedRiskEngine:
    """
    Unified Risk Engine with sovereign veto authority.
    Combines pre-trade, intraday, portfolio, leverage, liquidity, and kill switch controls.
    """

    MAX_PORTFOLIO_HEAT_PCT = 3.00
    MAX_GROSS_LEVERAGE = 3.00
    MAX_DAILY_DRAWDOWN_PCT = 5.00
    MAX_TOTAL_DRAWDOWN_PCT = 15.00
    MAX_ORDER_PRICE_DEVIATION_PCT = 3.00  # Price collar: 3% from mid
    MIN_MAINTENANCE_MARGIN_BUFFER = 0.20  # 20% margin buffer

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        firewall: Optional[PortfolioRiskFirewall] = None,
    ):
        self._audit_logger = audit_logger or AuditLogger()
        self._firewall = firewall or PortfolioRiskFirewall()
        self._kill_switch_state = KillSwitchState.ARMED_NORMAL
        self._kill_switch_reason: Optional[str] = None
        self._daily_starting_equity: Dict[str, float] = {}
        self._intraday_high_water_mark: Dict[str, float] = {}

    @property
    def kill_switch_state(self) -> KillSwitchState:
        return self._kill_switch_state

    def trigger_emergency_halt(self, reason: str, actor: str = "SYSTEM") -> None:
        """Immediately halts all new order submissions and triggers defense protocols."""
        self._kill_switch_state = KillSwitchState.EMERGENCY_HALT
        self._kill_switch_reason = f"EMERGENCY_HALT by {actor}: {reason}"
        self._audit_logger.log_event(
            event_type="EMERGENCY_HALT",
            actor=actor,
            action="TRIGGER",
            details={"reason": reason, "timestamp": SystemClock.utc_now().isoformat()},
        )
        logger.critical(f"EMERGENCY HALT TRIGGERED: {self._kill_switch_reason}")

    def trigger_hard_kill(self, reason: str, actor: str = "RISK_ADMIN") -> None:
        """Full system lock down requiring manual administrative clearance."""
        self._kill_switch_state = KillSwitchState.HARD_KILL
        self._kill_switch_reason = f"HARD_KILL by {actor}: {reason}"
        self._audit_logger.log_event(
            event_type="HARD_KILL",
            actor=actor,
            action="TRIGGER",
            details={"reason": reason, "timestamp": SystemClock.utc_now().isoformat()},
        )
        logger.critical(f"HARD KILL SWITCH ACTIVATED: {self._kill_switch_reason}")

    def reset_kill_switch(self, clearance_token: str, actor: str = "SUPER_ADMIN") -> bool:
        """Clears emergency halt if valid administrative authorization is provided."""
        if not clearance_token.startswith("CLEAR-RISK-"):
            logger.warning(f"Invalid clearance token presented by {actor}")
            return False

        previous = self._kill_switch_state
        self._kill_switch_state = KillSwitchState.ARMED_NORMAL
        self._kill_switch_reason = None
        self._audit_logger.log_event(
            event_type="KILL_SWITCH_RESET",
            actor=actor,
            action="RESET",
            details={"previous_state": previous.value},
        )
        return True

    def evaluate_account_economic_viability(
        self,
        order: PreTradeOrderSpec,
        min_viable_equity_usd: float = 250.0,
        roundtrip_friction_bps: float = 16.0,
        max_friction_to_risk_ratio_pct: float = 25.0,
    ) -> AccountViabilityResult:
        """
        Calculates whether an account is economically viable for the requested trade (Directive EABG-001).
        Prevents trading when transaction friction or lot size constraints dominate expected edge.
        Returns 'INSUFFICIENT CAPITAL / NO TRADE' if the account cannot safely support the trade.
        """
        equity = float(order.account_equity_usd)

        # 1. Minimum Viable Capital check
        if equity < min_viable_equity_usd:
            return AccountViabilityResult(
                is_viable=False,
                verdict="INSUFFICIENT CAPITAL / NO TRADE",
                account_equity_usd=equity,
                order_notional_usd=order.notional_usd,
                estimated_risk_usd=order.notional_usd * 0.02,
                total_friction_usd=order.notional_usd * (roundtrip_friction_bps / 10_000.0),
                friction_to_risk_ratio_pct=100.0,
                rejection_reason=(
                    f"Account equity ${equity:.2f} is below minimum viable threshold (${min_viable_equity_usd:.2f}). "
                    "Small accounts cannot safely absorb exchange lot minimums and fixed transaction friction."
                ),
            )

        # 2. Estimate trade risk
        risk_pct = 0.02
        if order.stop_loss_price and order.limit_price and order.limit_price > 0:
            risk_pct = abs(order.limit_price - order.stop_loss_price) / order.limit_price
        est_risk_usd = order.notional_usd * max(0.005, risk_pct)

        # 3. Estimate roundtrip friction
        total_friction_usd = order.notional_usd * (roundtrip_friction_bps / 10_000.0)
        friction_ratio = (total_friction_usd / max(0.01, est_risk_usd)) * 100.0

        if friction_ratio > max_friction_to_risk_ratio_pct:
            return AccountViabilityResult(
                is_viable=False,
                verdict="INSUFFICIENT CAPITAL / NO TRADE",
                account_equity_usd=equity,
                order_notional_usd=order.notional_usd,
                estimated_risk_usd=est_risk_usd,
                total_friction_usd=total_friction_usd,
                friction_to_risk_ratio_pct=friction_ratio,
                rejection_reason=(
                    f"Transaction friction (${total_friction_usd:.2f}, {friction_ratio:.1f}% of risk) "
                    f"dominates risk budget (ceiling {max_friction_to_risk_ratio_pct:.1f}%)."
                ),
            )

        # 4. Leverage sanity
        implied_leverage = order.notional_usd / max(1.0, equity)
        if implied_leverage > self.MAX_GROSS_LEVERAGE:
            return AccountViabilityResult(
                is_viable=False,
                verdict="INSUFFICIENT CAPITAL / NO TRADE",
                account_equity_usd=equity,
                order_notional_usd=order.notional_usd,
                estimated_risk_usd=est_risk_usd,
                total_friction_usd=total_friction_usd,
                friction_to_risk_ratio_pct=friction_ratio,
                rejection_reason=(
                    f"Order notional (${order.notional_usd:.2f}) forces {implied_leverage:.2f}x leverage "
                    f"exceeding maximum permitted {self.MAX_GROSS_LEVERAGE:.2f}x."
                ),
            )

        return AccountViabilityResult(
            is_viable=True,
            verdict="APPROVED",
            account_equity_usd=equity,
            order_notional_usd=order.notional_usd,
            estimated_risk_usd=est_risk_usd,
            total_friction_usd=total_friction_usd,
            friction_to_risk_ratio_pct=friction_ratio,
            rejection_reason=None,
        )

    def evaluate_pre_trade_risk(
        self,
        order: PreTradeOrderSpec,
        current_open_positions: List[Dict[str, Any]],
        current_drawdown_pct: float,
        current_portfolio_heat_pct: float,
    ) -> RiskCheckResult:
        """
        Executes exhaustive pre-trade risk evaluation.
        Vetoes order if any threshold or safety constraint is breached.
        """
        violations: List[str] = []

        # 1. Kill Switch Check
        if self._kill_switch_state in (KillSwitchState.EMERGENCY_HALT, KillSwitchState.HARD_KILL):
            violations.append(f"Kill Switch Active ({self._kill_switch_state.value}): {self._kill_switch_reason}")
            return RiskCheckResult(
                approved=False,
                risk_action=FirewallAction.REJECT,
                allocated_quantity=0.0,
                rejection_reasons=violations,
                kill_switch_state=self._kill_switch_state,
            )

        # 1.5. Economic Viability & Small Account Gating (Directive EABG-001)
        viability = self.evaluate_account_economic_viability(order)
        if not viability.is_viable:
            violations.append(f"{viability.verdict}: {viability.rejection_reason}")

        # 2. Drawdown circuit breaker
        if current_drawdown_pct >= self.MAX_TOTAL_DRAWDOWN_PCT:
            violations.append(
                f"Account drawdown {current_drawdown_pct:.2f}% exceeds circuit breaker ceiling {self.MAX_TOTAL_DRAWDOWN_PCT:.2f}%"
            )

        # 3. Price collar check
        if order.limit_price and order.current_market_price > 0:
            price_dev = abs(order.limit_price - order.current_market_price) / order.current_market_price * 100.0
            if price_dev > self.MAX_ORDER_PRICE_DEVIATION_PCT:
                violations.append(
                    f"Order price {order.limit_price} deviates {price_dev:.2f}% from market {order.current_market_price} (collar {self.MAX_ORDER_PRICE_DEVIATION_PCT}%)"
                )

        # 4. Stop-loss sanity & Heat check
        est_trade_risk_usd = order.notional_usd * 0.02  # Default 2% stop assumption
        if order.stop_loss_price and order.limit_price:
            calc_risk_pct = abs(order.limit_price - order.stop_loss_price) / order.limit_price
            est_trade_risk_usd = order.notional_usd * calc_risk_pct

        incremental_heat_pct = (est_trade_risk_usd / max(1.0, order.account_equity_usd)) * 100.0
        projected_heat_pct = current_portfolio_heat_pct + incremental_heat_pct

        if projected_heat_pct > self.MAX_PORTFOLIO_HEAT_PCT:
            violations.append(
                f"Projected portfolio heat {projected_heat_pct:.2f}% exceeds hard {self.MAX_PORTFOLIO_HEAT_PCT:.2f}% ceiling"
            )

        # 5. Gross leverage check
        total_open_notional = sum(float(p.get("notional_usd", 0.0)) for p in current_open_positions)
        projected_notional = total_open_notional + order.notional_usd
        gross_leverage = projected_notional / max(1.0, order.account_equity_usd)
        if gross_leverage > self.MAX_GROSS_LEVERAGE:
            violations.append(
                f"Gross leverage {gross_leverage:.2f}x exceeds ceiling {self.MAX_GROSS_LEVERAGE:.2f}x"
            )

        # 6. Evaluate via 7D Firewall
        peak_eq = order.account_equity_usd / max(0.01, 1.0 - (current_drawdown_pct / 100.0))
        firewall_eval = self._firewall.evaluate_order(
            candidate_symbol=order.symbol,
            candidate_direction=order.direction,
            intended_risk_usd=est_trade_risk_usd,
            intended_notional_usd=order.notional_usd,
            account_equity_usd=order.account_equity_usd,
            current_peak_equity_usd=peak_eq,
            open_positions=current_open_positions,
        )

        if firewall_eval.action == FirewallAction.REJECT:
            violations.extend(firewall_eval.rejection_reasons)

        approved = len(violations) == 0
        allocated_qty = order.quantity if approved else (order.quantity * 0.5 if firewall_eval.action == FirewallAction.APPROVE_REDUCED_RISK and not violations else 0.0)

        action = FirewallAction.APPROVE if approved else (FirewallAction.APPROVE_REDUCED_RISK if allocated_qty > 0 else FirewallAction.REJECT)

        self._audit_logger.log_event(
            event_type="PRE_TRADE_RISK_CHECK",
            actor=order.strategy_id,
            action="EVALUATE",
            details={
                "strategy_id": order.strategy_id,
                "symbol": order.symbol,
                "approved": approved,
                "allocated_quantity": allocated_qty,
                "action": action.value,
                "violations": violations,
            },
        )

        return RiskCheckResult(
            approved=approved,
            risk_action=action,
            allocated_quantity=allocated_qty,
            rejection_reasons=violations,
            kill_switch_state=self._kill_switch_state,
        )

    def approve_hedge(self, hedge_rec: Any) -> bool:
        """Risk Governor check for hedge orders. Vetoes if Kill switch active or violates heat."""
        if self._kill_switch_state != KillSwitchState.ARMED_NORMAL:
            return False
        if getattr(hedge_rec, "estimated_additional_heat_pct", 0.0) > 1.0:
            return False
        return True
