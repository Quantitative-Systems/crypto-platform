"""Crypto Trading Platform — Independent Fail-Closed Risk Firewall.

Implements the supreme pre-trade risk gatekeeper across 22 distinct boundaries:
1. Maximum Order Size
2. Maximum Position Size
3. Maximum Portfolio Exposure
4. Gross Leverage Limits
5. Asset Concentration Limits
6. Daily Loss Limits
7. High-Watermark Drawdown Limits
8. Stale Market Data
9. Stale Signals
10. Missing Telemetry
11. Clock Drift Protection
12. Exchange Disconnect Gate
13. Duplicate Order Protection
14. Runaway Order Loop Detection
15. Unknown Order State Freezing
16. Reconciliation Failure Freezing
17. Emergency / Global Kill Switch
18. Tenant-Level Kill Switch
19. Account-Level Kill Switch
20. Venue-Level Kill Switch
21. Strategy-Level Kill Switch
22. Instrument-Level Kill Switch

CRITICAL INVARIANT: The Risk Engine is strictly decoupled from strategy code.
On ANY violation or exception, it FAILS CLOSED: EXPECTED RESULT = NO NEW ORDER.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Set

from crypto_platform.core.domain import (
    AccountBalance,
    OrderIntent,
    OrderStatus,
    Position,
    RiskDecision,
    RiskState,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.core.interfaces import IRiskEngine
from .circuit_breakers import AccountCircuitBreaker, CircuitBreakerConfig, CircuitState
from .kill_switches import KillSwitchManager


class RiskFirewall(IRiskEngine):
    """22-Boundary Independent Fail-Closed Risk Firewall."""

    def __init__(
        self,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        max_order_notional: float = 50_000.0,
        min_order_notional: float = 5.0,
        max_position_notional: float = 100_000.0,
        max_portfolio_exposure: float = 250_000.0,
        max_price_deviation_pct: float = 0.03,      # 3% fat-finger limit
        max_signal_age_ms: int = 2000,              # 2 second max signal age
        max_market_data_age_ms: int = 5000,         # 5 second max ticker age
        max_clock_drift_ms: int = 3000,             # 3 second max clock drift
        max_gross_leverage: float = 2.0,            # 2x gross leverage cap
        max_asset_concentration_pct: float = 0.35,  # 35% max in one asset
        max_concurrent_strategy_trades: int = 5,
        max_orders_per_second: int = 5,
        dedup_window_ms: int = 5000,
    ):
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        self.kill_switches = KillSwitchManager()
        self.circuit_breakers: Dict[str, AccountCircuitBreaker] = {}

        self.max_order_notional = max_order_notional
        self.min_order_notional = min_order_notional
        self.max_position_notional = max_position_notional
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_price_deviation_pct = max_price_deviation_pct
        self.max_signal_age_ms = max_signal_age_ms
        self.max_market_data_age_ms = max_market_data_age_ms
        self.max_clock_drift_ms = max_clock_drift_ms
        self.max_gross_leverage = max_gross_leverage
        self.max_asset_concentration_pct = max_asset_concentration_pct
        self.max_concurrent_strategy_trades = max_concurrent_strategy_trades
        self.max_orders_per_second = max_orders_per_second
        self.dedup_window_ms = dedup_window_ms

        # State tracking
        self._order_timestamps: Dict[str, List[int]] = {}
        self._seen_intents: Dict[str, int] = {}  # intent_id -> timestamp_ms
        self._disconnected_venues: Set[str] = set()
        self._reconciliation_out_of_sync: Set[str] = set()  # account_ids
        self._accounts_with_unknown_orders: Set[str] = set()

    def set_venue_connected(self, venue: str, connected: bool) -> None:
        """Mark venue connection status."""
        v = venue.upper()
        if connected:
            self._disconnected_venues.discard(v)
        else:
            self._disconnected_venues.add(v)

    def set_reconciliation_status(self, account_id: str, in_sync: bool) -> None:
        """Mark account reconciliation state."""
        if in_sync:
            self._reconciliation_out_of_sync.discard(account_id)
        else:
            self._reconciliation_out_of_sync.add(account_id)

    def set_unknown_order_state(self, account_id: str, has_unknown: bool) -> None:
        """Flag if an account has unresolved UNKNOWN orders."""
        if has_unknown:
            self._accounts_with_unknown_orders.add(account_id)
        else:
            self._accounts_with_unknown_orders.discard(account_id)

    def get_or_create_circuit_breaker(
        self, account_id: str, equity: float = 100_000.0, initial_equity: Optional[float] = None
    ) -> AccountCircuitBreaker:
        eq = initial_equity if initial_equity is not None else equity
        if account_id not in self.circuit_breakers:
            self.circuit_breakers[account_id] = AccountCircuitBreaker(
                initial_equity=eq, config=self.circuit_config
            )
        return self.circuit_breakers[account_id]

    def update_account_state(self, equity: float, realized_pnl: float) -> None:
        pass

    def is_kill_switch_active(self, scope: str, target: str) -> bool:
        active, _ = self.kill_switches.is_active(
            tenant_id=target if scope == "TENANT" else "",
            account_id=target if scope == "ACCOUNT" else "",
            venue=target if scope == "VENUE" else "",
            strategy_id=target if scope == "STRATEGY" else "",
            symbol=target if scope == "INSTRUMENT" else "",
        )
        return active

    def evaluate_order_intent(
        self,
        intent: OrderIntent,
        current_positions: Dict[str, Position],
        balances: Dict[str, AccountBalance],
        risk_state: RiskState,
        latest_ticker: Optional[TickerEvent] = None,
        venue: str = "BINANCE",
    ) -> RiskDecision:
        """Evaluate order intent through all 22 risk boundaries.

        FAIL-CLOSED INVARIANT: Any violation or exception results in NO NEW ORDER.
        """
        now_ms = int(time.time() * 1000)

        try:
            # -----------------------------------------------------------------
            # BOUNDARY 1-6: Hierarchical Kill Switches
            # -----------------------------------------------------------------
            is_killed, kill_reason = self.kill_switches.is_active(
                tenant_id=intent.tenant_id,
                account_id=intent.account_id,
                venue=venue,
                strategy_id=intent.strategy_id,
                symbol=intent.symbol,
            )
            if is_killed:
                rule_code = "KILL_SWITCH_ACTIVE"
                if "GLOBAL" in kill_reason:
                    rule_code = "GLOBAL_KILL_SWITCH_ACTIVE"
                elif "TENANT" in kill_reason:
                    rule_code = "TENANT_KILL_SWITCH_ACTIVE"
                elif "ACCOUNT" in kill_reason:
                    rule_code = "ACCOUNT_KILL_SWITCH_ACTIVE"
                elif "VENUE" in kill_reason:
                    rule_code = "VENUE_KILL_SWITCH_ACTIVE"
                elif "STRATEGY" in kill_reason:
                    rule_code = "STRATEGY_KILL_SWITCH_ACTIVE"
                elif "INSTRUMENT" in kill_reason:
                    rule_code = "INSTRUMENT_KILL_SWITCH_ACTIVE"

                return RiskDecision(
                    approved=False,
                    reason=f"Rejected by Kill Switch: {kill_reason}",
                    rule_code=rule_code,
                )

            # -----------------------------------------------------------------
            # BOUNDARY 7: Venue Connectivity
            # -----------------------------------------------------------------
            if venue.upper() in self._disconnected_venues:
                return RiskDecision(
                    approved=False,
                    reason=f"Venue {venue} is currently disconnected",
                    rule_code="EXCHANGE_DISCONNECTED",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 8: Account Reconciliation Integrity
            # -----------------------------------------------------------------
            if intent.account_id in self._reconciliation_out_of_sync:
                return RiskDecision(
                    approved=False,
                    reason=f"Account {intent.account_id} reconciliation out of sync: trading frozen",
                    rule_code="RECONCILIATION_OUT_OF_SYNC",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 9: Unresolved Unknown Orders
            # -----------------------------------------------------------------
            if intent.account_id in self._accounts_with_unknown_orders:
                return RiskDecision(
                    approved=False,
                    reason=f"Account {intent.account_id} has unresolved UNKNOWN orders: trading frozen",
                    rule_code="UNKNOWN_ORDER_STATE_PENDING",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 10: Duplicate Order Detection
            # -----------------------------------------------------------------
            if intent.intent_id in self._seen_intents:
                prev_seen = self._seen_intents[intent.intent_id]
                if now_ms - prev_seen <= self.dedup_window_ms:
                    return RiskDecision(
                        approved=False,
                        reason=f"Duplicate order intent detected: {intent.intent_id}",
                        rule_code="DUPLICATE_ORDER",
                    )
            self._seen_intents[intent.intent_id] = now_ms

            # -----------------------------------------------------------------
            # BOUNDARY 11: Runaway Order Loop Detection
            # -----------------------------------------------------------------
            history = self._order_timestamps.setdefault(intent.account_id, [])
            history = [t for t in history if now_ms - t <= 1000]
            self._order_timestamps[intent.account_id] = history
            if len(history) >= self.max_orders_per_second:
                return RiskDecision(
                    approved=False,
                    reason=f"Runaway order rate limit exceeded: {len(history)} orders in last 1000ms",
                    rule_code="RUNAWAY_RATE_LIMIT",
                )
            history.append(now_ms)

            # -----------------------------------------------------------------
            # BOUNDARY 12: Missing Telemetry
            # -----------------------------------------------------------------
            if latest_ticker is None:
                return RiskDecision(
                    approved=False,
                    reason="Missing market ticker: cannot price or sanity-check order",
                    rule_code="MISSING_MARKET_DATA",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 13: Stale Market Data
            # -----------------------------------------------------------------
            ticker_age = now_ms - latest_ticker.timestamp_ms
            if ticker_age > self.max_market_data_age_ms:
                return RiskDecision(
                    approved=False,
                    reason=f"Stale market data: ticker age {ticker_age}ms > {self.max_market_data_age_ms}ms",
                    rule_code="STALE_MARKET_DATA",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 14: Clock Drift Protection
            # -----------------------------------------------------------------
            clock_drift = abs(now_ms - latest_ticker.timestamp_ms)
            if clock_drift > self.max_clock_drift_ms or intent.created_at_ms > now_ms + 1000:
                return RiskDecision(
                    approved=False,
                    reason=f"Clock drift exceeded: {clock_drift}ms > max {self.max_clock_drift_ms}ms",
                    rule_code="CLOCK_DRIFT_EXCEEDED",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 15: Stale Signal
            # -----------------------------------------------------------------
            signal_age = now_ms - intent.created_at_ms
            if signal_age > self.max_signal_age_ms:
                return RiskDecision(
                    approved=False,
                    reason=f"Stale signal: age {signal_age}ms > {self.max_signal_age_ms}ms",
                    rule_code="STALE_SIGNAL",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 16 & 17: Daily Loss & Drawdown Limits (Circuit Breaker)
            # -----------------------------------------------------------------
            cb = self.get_or_create_circuit_breaker(intent.account_id, risk_state.equity)
            cb_state = cb.update_equity(risk_state.equity)

            if cb_state == CircuitState.CIRCUIT_TRIP:
                return RiskDecision(
                    approved=False,
                    reason=f"Daily Loss Limit breached: {cb.trip_reason}",
                    rule_code="DAILY_LOSS_LIMIT_BREACH",
                )
            elif cb_state == CircuitState.SAFE_MODE:
                return RiskDecision(
                    approved=False,
                    reason=f"Account locked in SAFE_MODE (Drawdown Limit): {cb.trip_reason}",
                    rule_code="DRAWDOWN_LIMIT_BREACH",
                )

            size_multiplier = cb.get_sizing_multiplier()
            adjusted_size = intent.target_size * size_multiplier
            if adjusted_size <= 0:
                return RiskDecision(
                    approved=False,
                    reason="Circuit breaker size multiplier throttled size to zero",
                    rule_code="SIZE_THROTTLED_ZERO",
                )

            # Price calculations
            ref_price = latest_ticker.last_price
            if ref_price <= 0:
                return RiskDecision(
                    approved=False,
                    reason="Invalid market price (<=0)",
                    rule_code="INVALID_MARKET_PRICE",
                )

            order_notional = adjusted_size * ref_price

            # -----------------------------------------------------------------
            # BOUNDARY 18: Maximum & Minimum Order Size
            # -----------------------------------------------------------------
            if order_notional < self.min_order_notional:
                return RiskDecision(
                    approved=False,
                    reason=f"Order notional ${order_notional:.2f} < minimum ${self.min_order_notional:.2f}",
                    rule_code="MIN_NOTIONAL_BREACH",
                )
            if order_notional > self.max_order_notional:
                return RiskDecision(
                    approved=False,
                    reason=f"Order notional ${order_notional:.2f} > maximum order notional ${self.max_order_notional:.2f}",
                    rule_code="MAX_NOTIONAL_BREACH",
                )

            # Fat-finger price check
            if intent.limit_price is not None and intent.limit_price > 0:
                dev = abs(intent.limit_price - ref_price) / ref_price
                if dev > self.max_price_deviation_pct:
                    return RiskDecision(
                        approved=False,
                        reason=f"Fat-finger price deviation: {dev*100:.2f}% > {self.max_price_deviation_pct*100:.2f}%",
                        rule_code="FAT_FINGER_PRICE_DEVIATION",
                    )

            # -----------------------------------------------------------------
            # BOUNDARY 19: Maximum Position Size
            # -----------------------------------------------------------------
            existing_pos = current_positions.get(intent.symbol)
            existing_notional = abs(existing_pos.size * existing_pos.mark_price) if existing_pos else 0.0
            new_pos_notional = existing_notional + order_notional
            if new_pos_notional > self.max_position_notional:
                return RiskDecision(
                    approved=False,
                    reason=f"Position size breach on {intent.symbol}: ${new_pos_notional:.2f} > max ${self.max_position_notional:.2f}",
                    rule_code="MAX_POSITION_SIZE_BREACH",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 20: Maximum Portfolio Exposure
            # -----------------------------------------------------------------
            current_total_notional = sum(
                abs(p.size * p.mark_price) for p in current_positions.values()
            )
            new_total_notional = current_total_notional + order_notional
            if new_total_notional > self.max_portfolio_exposure:
                return RiskDecision(
                    approved=False,
                    reason=f"Portfolio exposure breach: ${new_total_notional:.2f} > max ${self.max_portfolio_exposure:.2f}",
                    rule_code="MAX_PORTFOLIO_EXPOSURE_BREACH",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 21: Gross Leverage Limit
            # -----------------------------------------------------------------
            current_equity = max(1.0, risk_state.equity)
            new_leverage = new_total_notional / current_equity
            if new_leverage > self.max_gross_leverage:
                return RiskDecision(
                    approved=False,
                    reason=f"Gross leverage breach: {new_leverage:.2f}x > max {self.max_gross_leverage:.2f}x",
                    rule_code="LEVERAGE_LIMIT_BREACH",
                )

            # -----------------------------------------------------------------
            # BOUNDARY 22: Asset Concentration Limit
            # -----------------------------------------------------------------
            sym_concentration = new_pos_notional / current_equity
            if sym_concentration > self.max_asset_concentration_pct:
                return RiskDecision(
                    approved=False,
                    reason=f"Single-asset concentration breach: {sym_concentration*100:.1f}% > {self.max_asset_concentration_pct*100:.1f}%",
                    rule_code="CONCENTRATION_LIMIT_BREACH",
                )

            # All 22 boundaries passed!
            return RiskDecision(
                approved=True,
                reason="All 22 pre-trade risk boundaries passed",
                rule_code="PASS",
                adjusted_size=adjusted_size,
            )

        except Exception as e:
            # FAIL-CLOSED INVARIANT: Never allow a trade if risk check errors out
            return RiskDecision(
                approved=False,
                reason=f"RISK_FAIL_CLOSED_EXCEPTION: {str(e)}",
                rule_code="FAIL_CLOSED",
            )
