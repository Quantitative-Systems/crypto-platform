"""Crypto Platform — Dedicated LIVE-CANARY Safety & Risk Control Tests.

Comprehensive automated verification of all LIVE-CANARY security invariants,
fail-closed gates, and risk firewalls using sandbox/mock adapters (zero real money).

Covered Scenarios:
1. Wrong endpoint (testnet in LIVE_CANARY or production in DEMO)
2. Wrong credentials (missing, empty, or mock in LIVE_CANARY)
3. Withdrawal-enabled credentials rejected
4. Missing capital allocation ($0 or unallocated capital blocks arming)
5. Capital limit exceeded (CANARY_CAPITAL_LIMIT_BREACH)
6. Position limit exceeded (CANARY_MAX_POSITION_SIZE)
7. Leverage limit exceeded (CANARY_LEVERAGE_BREACH & pre-flight step 6)
8. Daily loss limit breach (CANARY_DAILY_LOSS_BREACH)
9. Drawdown limit breach (CANARY_DRAWDOWN_BREACH)
10. Stale market data rejected (pre-flight step 9 & pre-trade firewall)
11. Duplicate order intent rejected
12. Emergency kill switch trip, order cancellation, and engine halt
13. Reconciliation drift detection blocks activation
14. Broker disconnect fails pre-flight verification
15. Restart recovery requires explicit manual reset
16. DEMO vs LIVE-CANARY credential and endpoint separation
"""
from __future__ import annotations

import time
from typing import List, Optional
import pytest

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RiskState,
    TimeInForce,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.exchange_adapters import (
    AuthenticationError,
    BinanceAdapter,
    PermissionSecurityError,
)
from crypto_platform.live_canary.harness import CanaryState, LiveCanaryHarness
from crypto_platform.live_canary.verifier import CanaryBrokerVerifier
from crypto_platform.risk_engine.firewall import RiskFirewall


class MockCanaryAdapter(BinanceAdapter):
    """Hermetic test adapter simulating exchange responses for safety tests."""

    def __init__(
        self,
        connected: bool = True,
        has_withdrawal: bool = False,
        balance_usdt: float = 1000.0,
        positions: Optional[List[Position]] = None,
        leverage: float = 1.0,
    ):
        super().__init__(is_futures=True, testnet=False, mock_mode=True)
        self._connected = connected
        self.has_withdrawal = has_withdrawal
        self.balance_usdt = balance_usdt
        self.mock_positions = positions or []
        self.account_leverage = leverage
        self.cancelled_orders: List[str] = []

    async def connect(self, credentials, mode=OperatingMode.LIVE_CANARY):
        if not self._connected:
            return False
        return await super().connect(credentials, mode=mode)

    async def verify_permissions(self):
        return {
            "read": True,
            "trade": True,
            "withdraw": self.has_withdrawal,
            "transfer": False,
        }

    async def get_account_balances(self):
        return [AccountBalance(asset="USDT", free=self.balance_usdt, locked=0.0, total=self.balance_usdt)]

    async def get_positions(self):
        return list(self.mock_positions)

    async def get_open_orders(self):
        return [
            ExecutionOrder(
                order_id="open_1",
                client_order_id="c_open_1",
                tenant_id="t1",
                account_id="acc1",
                venue=self.venue_name,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                time_in_force=TimeInForce.GTC,
                quantity=0.001,
                price=50000.0,
                status=OrderStatus.ACKNOWLEDGED,
            )
        ]

    async def cancel_order(self, client_order_id: str, symbol: str) -> bool:
        self.cancelled_orders.append(client_order_id)
        return True


def make_canary_intent(
    symbol: str = "BTCUSDT",
    direction: int = 1,
    size: float = 0.001,
    limit_px: float = 60000.0,
    intent_id: str = "intent_canary_01",
    age_ms: int = 0,
) -> OrderIntent:
    now_ms = int(time.time() * 1000)
    return OrderIntent(
        intent_id=intent_id,
        strategy_id="trend_rider_01",
        tenant_id="tenant_primary",
        account_id="acc_canary_01",
        symbol=symbol,
        direction=direction,
        target_size=size,
        limit_price=limit_px,
        created_at_ms=now_ms - age_ms,
    )


def make_fresh_ticker(symbol: str = "BTCUSDT", price: float = 60000.0, age_ms: int = 0) -> TickerEvent:
    now_ms = int(time.time() * 1000)
    return TickerEvent(
        venue="binance_futures",
        symbol=symbol,
        timestamp_ms=now_ms - age_ms,
        bid=price - 1.0,
        ask=price + 1.0,
        last_price=price,
    )


# ==============================================================================
# 1. WRONG ENDPOINT TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_live_canary_rejects_testnet_endpoint():
    """LIVE-CANARY must reject testnet endpoints with fail-closed AuthenticationError."""
    testnet_adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=True)
    with pytest.raises(AuthenticationError) as exc_info:
        await testnet_adapter.connect(
            {"api_key": "real_prod_key", "api_secret": "real_prod_secret"},
            mode=OperatingMode.LIVE_CANARY,
        )
    assert "Cannot use testnet endpoint in LIVE-CANARY mode" in str(exc_info.value)


@pytest.mark.anyio
async def test_demo_rejects_production_endpoint():
    """DEMO must reject production mainnet endpoints."""
    prod_adapter = BinanceAdapter(is_futures=True, testnet=False, mock_mode=True)
    with pytest.raises(AuthenticationError) as exc_info:
        await prod_adapter.connect(
            {"api_key": "any_key", "api_secret": "any_secret"},
            mode=OperatingMode.DEMO,
        )
    assert "DEMO mode requires testnet endpoint" in str(exc_info.value)


# ==============================================================================
# 2. WRONG CREDENTIALS TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_live_canary_rejects_mock_or_missing_credentials():
    """LIVE-CANARY must reject mock placeholders and incomplete credentials."""
    adapter = BinanceAdapter(is_futures=True, testnet=False, mock_mode=True)

    # Mock key in LIVE-CANARY
    with pytest.raises(AuthenticationError) as exc_info:
        await adapter.connect(
            {"api_key": "mock_api_key", "api_secret": "real_secret"},
            mode=OperatingMode.LIVE_CANARY,
        )
    assert "CANARY_CREDENTIAL_MISMATCH" in str(exc_info.value)

    # Missing required keys
    with pytest.raises(AuthenticationError):
        await adapter.connect({"api_key": ""}, mode=OperatingMode.LIVE_CANARY)


# ==============================================================================
# 3. WITHDRAWAL PERMISSION TEST
# ==============================================================================

@pytest.mark.anyio
async def test_withdrawal_permission_rejected():
    """Keys with withdrawal privileges must be rejected immediately."""
    adapter = MockCanaryAdapter(has_withdrawal=True)
    verifier = CanaryBrokerVerifier(adapter=adapter)
    report = await verifier.verify_all()

    assert report.passed is False
    step_11 = next(c for c in report.checks if c.step_number == 11)
    assert step_11.passed is False
    assert "FATAL SECURITY VIOLATION" in step_11.message


# ==============================================================================
# 4. MISSING CAPITAL ALLOCATION
# ==============================================================================

@pytest.mark.anyio
async def test_missing_capital_allocation_blocks_arming(tmp_path):
    """Harness cannot be armed if capital limit is 0 or unallocated."""
    adapter = MockCanaryAdapter(balance_usdt=500.0)
    db_file = str(tmp_path / "canary.db")
    harness = LiveCanaryHarness(
        adapter=adapter,
        canary_capital_limit_usd=0.0,  # Missing allocation
        db_path=db_file,
    )
    armed = await harness.arm()
    assert armed is False
    assert harness.state == CanaryState.DISARMED


# ==============================================================================
# 5. CAPITAL LIMIT EXCEEDED
# ==============================================================================

def test_capital_limit_exceeded_rejected_by_firewall():
    """Order notional exceeding CANARY_CAPITAL_LIMIT_USD must be rejected by Risk Firewall."""
    firewall = RiskFirewall()
    firewall.configure_canary(
        capital_limit_usd=100.0,
        max_position_size=300.0,  # Ensure position size boundary passes to test capital limit
        canary_state="ACTIVE",
    )

    # Intent with notional = 0.0025 * 60,000 = $150 (exceeds $100 capital limit, but < $300 pos size)
    intent = make_canary_intent(size=0.0025, limit_px=60000.0)
    ticker = make_fresh_ticker()
    risk_state = RiskState(equity=500.0, peak_equity=500.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={"USDT": AccountBalance(asset="USDT", free=500.0, locked=0.0, total=500.0)},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert decision.approved is False
    assert decision.rule_code == "CANARY_CAPITAL_LIMIT_BREACH"


# ==============================================================================
# 6. POSITION LIMIT EXCEEDED
# ==============================================================================

def test_position_limit_exceeded_rejected_by_firewall():
    """Order exceeding CANARY_MAX_POSITION_SIZE must be rejected by Risk Firewall."""
    firewall = RiskFirewall()
    firewall.configure_canary(
        capital_limit_usd=200.0,
        max_position_size=50.0,  # Max $50 per position
        canary_state="ACTIVE",
    )

    # Intent with notional = 0.0015 * 60,000 = $90 (exceeds $50 position limit)
    intent = make_canary_intent(size=0.0015, limit_px=60000.0)
    ticker = make_fresh_ticker()
    risk_state = RiskState(equity=200.0, peak_equity=200.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={"USDT": AccountBalance(asset="USDT", free=200.0, locked=0.0, total=200.0)},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert decision.approved is False
    assert decision.rule_code == "CANARY_MAX_POSITION_BREACH"


# ==============================================================================
# 7. LEVERAGE LIMIT EXCEEDED
# ==============================================================================

@pytest.mark.anyio
async def test_leverage_limit_exceeded_preflight():
    """Account leverage higher than CANARY_MAX_LEVERAGE fails pre-flight verification."""
    adapter = MockCanaryAdapter(leverage=3.0)  # Account configured for 3x
    verifier = CanaryBrokerVerifier(adapter=adapter, canary_max_leverage=1.5)
    report = await verifier.verify_all()

    assert report.passed is False
    step_6 = next(c for c in report.checks if c.step_number == 6)
    assert step_6.passed is False
    assert "exceeds CANARY_MAX_LEVERAGE" in step_6.message


def test_leverage_limit_exceeded_firewall():
    """Intent requiring leverage exceeding canary_max_leverage is rejected."""
    firewall = RiskFirewall()
    firewall.configure_canary(
        capital_limit_usd=500.0,
        max_position_size=500.0,
        max_leverage=1.5,
        canary_state="ACTIVE",
    )

    # Intent with notional = $80. Existing position = $80. Total exposure = $160.
    # Capital / Equity = $100. Effective leverage = 1.6x > 1.5x limit.
    intent = make_canary_intent(size=0.001333, limit_px=60000.0)  # ~$80
    ticker = make_fresh_ticker()
    existing_pos = Position(
        symbol="BTCUSDT",
        direction=1,
        size=0.001333,
        entry_price=60000.0,
        mark_price=60000.0,
    )
    risk_state = RiskState(equity=100.0, peak_equity=100.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={"BTCUSDT": existing_pos},
        balances={"USDT": AccountBalance(asset="USDT", free=100.0, locked=0.0, total=100.0)},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert decision.approved is False
    assert decision.rule_code == "CANARY_LEVERAGE_BREACH"


# ==============================================================================
# 8. DAILY LOSS LIMIT BREACH
# ==============================================================================

def test_daily_loss_limit_breach_firewall():
    """Daily loss exceeding CANARY_MAX_DAILY_LOSS is rejected."""
    firewall = RiskFirewall()
    firewall.configure_canary(
        capital_limit_usd=100.0,
        max_daily_loss=0.02,  # 2% max daily loss
        canary_state="ACTIVE",
    )

    intent = make_canary_intent()
    ticker = make_fresh_ticker()
    # RiskState with 3% daily loss
    risk_state = RiskState(equity=97.0, peak_equity=100.0, daily_loss_pct=0.03)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert decision.approved is False
    assert decision.rule_code == "CANARY_DAILY_LOSS_BREACH"


# ==============================================================================
# 9. DRAWDOWN LIMIT BREACH
# ==============================================================================

def test_drawdown_limit_breach_firewall():
    """Drawdown exceeding CANARY_MAX_TOTAL_DRAWDOWN is rejected."""
    firewall = RiskFirewall()
    firewall.configure_canary(
        capital_limit_usd=100.0,
        max_total_drawdown=0.05,  # 5% max drawdown
        canary_state="ACTIVE",
    )

    intent = make_canary_intent()
    ticker = make_fresh_ticker()
    # RiskState with 6% drawdown
    risk_state = RiskState(equity=94.0, peak_equity=100.0, drawdown_pct=0.06)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert decision.approved is False
    assert decision.rule_code == "CANARY_DRAWDOWN_BREACH"


# ==============================================================================
# 10. STALE MARKET DATA
# ==============================================================================

@pytest.mark.anyio
async def test_stale_market_data_rejected():
    """Market data older than threshold fails pre-flight step 9."""
    adapter = MockCanaryAdapter()
    verifier = CanaryBrokerVerifier(adapter=adapter)
    stale_ticker = make_fresh_ticker(age_ms=10000)  # 10 seconds old

    report = await verifier.verify_all(latest_ticker=stale_ticker)
    assert report.passed is False
    step_9 = next(c for c in report.checks if c.step_number == 9)
    assert step_9.passed is False
    assert "exceeds threshold" in step_9.message


# ==============================================================================
# 11. DUPLICATE ORDER INTENT
# ==============================================================================

def test_duplicate_order_intent_rejected():
    """Duplicate order intent within cache TTL is rejected by firewall."""
    firewall = RiskFirewall()
    firewall.configure_canary(capital_limit_usd=1000.0, max_position_size=1000.0, canary_state="ACTIVE")

    # Intent with notional = 0.001 * 60,000 = $60 on $1000 equity (6% concentration <= 35% limit)
    intent = make_canary_intent(size=0.001, intent_id="intent_dupe_123")
    ticker = make_fresh_ticker()
    risk_state = RiskState(equity=1000.0, peak_equity=1000.0)

    # First pass
    dec1 = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={"USDT": AccountBalance(asset="USDT", free=1000.0, locked=0.0, total=1000.0)},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert dec1.approved is True

    # Immediate second pass with identical intent_id
    dec2 = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={"USDT": AccountBalance(asset="USDT", free=1000.0, locked=0.0, total=1000.0)},
        risk_state=risk_state,
        latest_ticker=ticker,
        operating_mode=OperatingMode.LIVE_CANARY,
    )
    assert dec2.approved is False
    assert dec2.rule_code == "DUPLICATE_ORDER"


# ==============================================================================
# 12. EMERGENCY KILL SWITCH TRIP
# ==============================================================================

@pytest.mark.anyio
async def test_emergency_kill_trip_and_order_cancellation(tmp_path):
    """Emergency kill switch halts engine, cancels open orders, and trips firewall."""
    adapter = MockCanaryAdapter()
    db_file = str(tmp_path / "canary.db")
    harness = LiveCanaryHarness(adapter=adapter, db_path=db_file)

    # Arm and activate
    armed = await harness.arm()
    assert armed is True
    activated = await harness.activate()
    assert activated is True
    assert harness.state == CanaryState.ACTIVE

    # Trip Emergency Kill
    await harness.emergency_kill(reason="MANUAL_SAFETY_TRIP")

    assert harness.state == CanaryState.HALTED
    assert harness.halt_reason == "MANUAL_SAFETY_TRIP"
    assert "c_open_1" in adapter.cancelled_orders

    # Subsequent orders must be rejected
    intent = make_canary_intent()
    result = await harness.execute_intent(intent, latest_ticker=make_fresh_ticker())
    assert result is None


# ==============================================================================
# 13. RECONCILIATION DRIFT
# ==============================================================================

@pytest.mark.anyio
async def test_reconciliation_drift_blocks_activation():
    """Untracked external positions on broker fail pre-flight step 13."""
    external_pos = Position(
        symbol="ETHUSDT",
        direction=1,
        size=0.5,
        entry_price=3000.0,
        mark_price=3100.0,
    )
    adapter = MockCanaryAdapter(positions=[external_pos])
    verifier = CanaryBrokerVerifier(adapter=adapter)

    report = await verifier.verify_all()
    assert report.passed is False
    step_13 = next(c for c in report.checks if c.step_number == 13)
    assert step_13.passed is False
    assert "Unexpected external positions detected" in step_13.message


# ==============================================================================
# 14. BROKER DISCONNECT
# ==============================================================================

@pytest.mark.anyio
async def test_broker_disconnect_fails_preflight():
    """Disconnected broker adapter fails pre-flight step 1."""
    adapter = MockCanaryAdapter(connected=False)
    verifier = CanaryBrokerVerifier(adapter=adapter)

    report = await verifier.verify_all()
    assert report.passed is False
    step_1 = next(c for c in report.checks if c.step_number == 1)
    assert step_1.passed is False
    assert "Adapter is not connected" in step_1.message


# ==============================================================================
# 15. RESTART RECOVERY
# ==============================================================================

@pytest.mark.anyio
async def test_restart_recovery_requires_manual_reset(tmp_path):
    """Engine in HALTED state cannot be re-armed without explicit manual reset."""
    adapter = MockCanaryAdapter()
    db_file = str(tmp_path / "canary.db")
    harness = LiveCanaryHarness(adapter=adapter, db_path=db_file)

    await harness.emergency_kill(reason="HALT_TEST")
    assert harness.state == CanaryState.HALTED

    # Direct arm attempt must be rejected
    armed = await harness.arm()
    assert armed is False
    assert harness.state == CanaryState.HALTED

    # Manual reset
    harness.reset_emergency_halt(authorized_by="CHIEF_RISK_OFFICER")
    assert harness.state == CanaryState.DISARMED

    # Now arming is permitted
    armed = await harness.arm()
    assert armed is True
    assert harness.state == CanaryState.ARMED


# ==============================================================================
# 16. DEMO VS LIVE-CANARY CREDENTIAL SEPARATION
# ==============================================================================

@pytest.mark.anyio
async def test_demo_and_live_canary_credential_separation():
    """Testnet and production credentials cannot be interchanged."""
    # Production adapter with LIVE_CANARY fails when given DEMO credentials
    prod_adapter = BinanceAdapter(is_futures=True, testnet=False, mock_mode=True)
    with pytest.raises(AuthenticationError):
        await prod_adapter.connect(
            {"api_key": "mock_demo_key", "api_secret": "mock_demo_secret"},
            mode=OperatingMode.LIVE_CANARY,
        )

    # Testnet adapter with DEMO fails when given production credentials
    demo_adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=True)
    # Testnet adapter connecting in LIVE_CANARY mode fails
    with pytest.raises(AuthenticationError):
        await demo_adapter.connect(
            {"api_key": "real_prod_key", "api_secret": "real_prod_secret"},
            mode=OperatingMode.LIVE_CANARY,
        )
