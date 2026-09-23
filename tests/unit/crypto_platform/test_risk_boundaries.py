"""Comprehensive failure-injection test suite for all 22 Risk Engine boundaries.

Verifies the strict fail-closed invariant:
FOR EVERY FAILURE: EXPECTED RESULT = NO NEW ORDER.
"""
import time
import pytest
from crypto_platform.core.domain import (
    AccountBalance,
    OrderIntent,
    Position,
    RiskState,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.risk_engine.circuit_breakers import CircuitBreakerConfig
from crypto_platform.risk_engine.firewall import RiskFirewall


@pytest.fixture
def firewall():
    cb_cfg = CircuitBreakerConfig(
        daily_derisk_pct=0.03,
        daily_halt_pct=0.05,
        max_hwm_drawdown_pct=0.12,
    )
    return RiskFirewall(
        circuit_config=cb_cfg,
        max_order_notional=10_000.0,
        min_order_notional=10.0,
        max_position_notional=25_000.0,
        max_portfolio_exposure=50_000.0,
        max_gross_leverage=2.0,
        max_asset_concentration_pct=0.35,
        max_market_data_age_ms=1000,
        max_signal_age_ms=1000,
        max_clock_drift_ms=2000,
        max_orders_per_second=3,
    )


@pytest.fixture
def valid_ticker():
    now_ms = int(time.time() * 1000)
    return TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms,
        bid=60000.0,
        ask=60002.0,
        last_price=60001.0,
    )


@pytest.fixture
def valid_intent():
    now_ms = int(time.time() * 1000)
    return OrderIntent(
        intent_id=f"intent_{now_ms}",
        strategy_id="strat_trend_01",
        tenant_id="t_001",
        account_id="acct_001",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,  # 0.1 * 60000 = $6000
        created_at_ms=now_ms,
    )


@pytest.fixture
def valid_balances():
    return {"USDT": AccountBalance(asset="USDT", free=50000.0, locked=0.0, total=50000.0)}


@pytest.fixture
def valid_risk_state():
    return RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0)


# =============================================================================
# 1-6. KILL SWITCHES
# =============================================================================
def test_boundary_global_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("GLOBAL", "*", "Emergency global halt")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "GLOBAL_KILL_SWITCH_ACTIVE"


def test_boundary_tenant_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("TENANT", valid_intent.tenant_id, "Tenant suspended")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "TENANT_KILL_SWITCH_ACTIVE"


def test_boundary_account_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("ACCOUNT", valid_intent.account_id, "Account margin call")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "ACCOUNT_KILL_SWITCH_ACTIVE"


def test_boundary_venue_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("VENUE", "BINANCE", "Binance API degraded")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker, venue="BINANCE")
    assert dec.approved is False
    assert dec.rule_code == "VENUE_KILL_SWITCH_ACTIVE"


def test_boundary_strategy_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("STRATEGY", valid_intent.strategy_id, "Strategy bug detected")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "STRATEGY_KILL_SWITCH_ACTIVE"


def test_boundary_instrument_kill_switch(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.kill_switches.activate("INSTRUMENT", "BTCUSDT", "BTC de-pegging volatility")
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "INSTRUMENT_KILL_SWITCH_ACTIVE"


# =============================================================================
# 7. VENUE CONNECTIVITY
# =============================================================================
def test_boundary_venue_disconnected(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.set_venue_connected("BINANCE", False)
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker, venue="BINANCE")
    assert dec.approved is False
    assert dec.rule_code == "EXCHANGE_DISCONNECTED"


# =============================================================================
# 8. ACCOUNT RECONCILIATION FAILURE
# =============================================================================
def test_boundary_reconciliation_failure(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.set_reconciliation_status(valid_intent.account_id, False)
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "RECONCILIATION_OUT_OF_SYNC"


# =============================================================================
# 9. UNKNOWN ORDER STATE
# =============================================================================
def test_boundary_unknown_order_state(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    firewall.set_unknown_order_state(valid_intent.account_id, True)
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "UNKNOWN_ORDER_STATE_PENDING"


# =============================================================================
# 10. DUPLICATE ORDER
# =============================================================================
def test_boundary_duplicate_order(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    # First pass passes
    dec1 = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec1.approved is True
    # Immediate retry with same intent_id fails
    dec2 = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec2.approved is False
    assert dec2.rule_code == "DUPLICATE_ORDER"


# =============================================================================
# 11. RUNAWAY ORDER LOOP
# =============================================================================
def test_boundary_runaway_order_loop(firewall, valid_balances, valid_risk_state, valid_ticker):
    now_ms = int(time.time() * 1000)
    for i in range(firewall.max_orders_per_second):
        intent = OrderIntent(
            intent_id=f"intent_loop_{i}",
            strategy_id="strat_01",
            tenant_id="t_001",
            account_id="acct_001",
            symbol="BTCUSDT",
            direction=1,
            target_size=0.01,
            created_at_ms=now_ms,
        )
        dec = firewall.evaluate_order_intent(intent, {}, valid_balances, valid_risk_state, valid_ticker)
        assert dec.approved is True

    # Next order immediately exceeds rate limit
    intent_extra = OrderIntent(
        intent_id="intent_loop_overflow",
        strategy_id="strat_01",
        tenant_id="t_001",
        account_id="acct_001",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.01,
        created_at_ms=now_ms,
    )
    dec_overflow = firewall.evaluate_order_intent(intent_extra, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec_overflow.approved is False
    assert dec_overflow.rule_code == "RUNAWAY_RATE_LIMIT"


# =============================================================================
# 12. MISSING TELEMETRY
# =============================================================================
def test_boundary_missing_telemetry(firewall, valid_intent, valid_balances, valid_risk_state):
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, latest_ticker=None)
    assert dec.approved is False
    assert dec.rule_code == "MISSING_MARKET_DATA"


# =============================================================================
# 13. STALE MARKET DATA
# =============================================================================
def test_boundary_stale_market_data(firewall, valid_intent, valid_balances, valid_risk_state):
    now_ms = int(time.time() * 1000)
    stale_ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms - 1500,  # 1500ms > 1000ms max
        bid=60000.0,
        ask=60002.0,
        last_price=60001.0,
    )
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, stale_ticker)
    assert dec.approved is False
    assert dec.rule_code == "STALE_MARKET_DATA"


# =============================================================================
# 14. CLOCK DRIFT
# =============================================================================
def test_boundary_clock_drift(firewall, valid_intent, valid_balances, valid_risk_state):
    now_ms = int(time.time() * 1000)
    future_ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms + 4000,  # 4000ms drift > 2000ms max
        bid=60000.0,
        ask=60002.0,
        last_price=60001.0,
    )
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, valid_risk_state, future_ticker)
    assert dec.approved is False
    assert dec.rule_code == "CLOCK_DRIFT_EXCEEDED"


# =============================================================================
# 15. STALE SIGNAL
# =============================================================================
def test_boundary_stale_signal(firewall, valid_balances, valid_risk_state, valid_ticker):
    now_ms = int(time.time() * 1000)
    stale_intent = OrderIntent(
        intent_id=f"intent_stale_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_001",
        account_id="acct_001",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        created_at_ms=now_ms - 2000,  # 2000ms > 1000ms max
    )
    dec = firewall.evaluate_order_intent(stale_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "STALE_SIGNAL"


# =============================================================================
# 16. DAILY LOSS LIMIT
# =============================================================================
def test_boundary_daily_loss_limit(firewall, valid_intent, valid_balances, valid_ticker):
    # Setup account circuit breaker with a day start of 100k and equity dropped to 94k (-6% > -5%)
    cb = firewall.get_or_create_circuit_breaker(valid_intent.account_id, 100000.0)
    cb.day_start_equity = 100000.0
    bad_state = RiskState(equity=94000.0, peak_equity=100000.0, drawdown_pct=0.06)

    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, bad_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "DAILY_LOSS_LIMIT_BREACH"


# =============================================================================
# 17. DRAWDOWN LIMIT (SAFE MODE)
# =============================================================================
def test_boundary_drawdown_limit(firewall, valid_intent, valid_balances, valid_ticker):
    # Setup account circuit breaker with HWM 100k and equity dropped to 85k (-15% > -12%)
    cb = firewall.get_or_create_circuit_breaker(valid_intent.account_id, 100000.0)
    bad_state = RiskState(equity=85000.0, peak_equity=100000.0, drawdown_pct=0.15)

    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, bad_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "DRAWDOWN_LIMIT_BREACH"


# =============================================================================
# 18. MAXIMUM ORDER SIZE
# =============================================================================
def test_boundary_max_order_size(firewall, valid_balances, valid_risk_state, valid_ticker):
    now_ms = int(time.time() * 1000)
    huge_intent = OrderIntent(
        intent_id=f"intent_huge_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_001",
        account_id="acct_001",
        symbol="BTCUSDT",
        direction=1,
        target_size=1.0,  # 1.0 * 60000 = $60,000 > max $10,000
        created_at_ms=now_ms,
    )
    dec = firewall.evaluate_order_intent(huge_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "MAX_NOTIONAL_BREACH"


# =============================================================================
# 19. MAXIMUM POSITION SIZE
# =============================================================================
def test_boundary_max_position_size(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    # Existing position is already $22,000. New order is $6,000 -> $28,000 > max $25,000
    existing_pos = {
        "BTCUSDT": Position(
            symbol="BTCUSDT", direction=1, size=0.3666, entry_price=60000.0, mark_price=60000.0
        )
    }
    dec = firewall.evaluate_order_intent(valid_intent, existing_pos, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "MAX_POSITION_SIZE_BREACH"


# =============================================================================
# 20. MAXIMUM PORTFOLIO EXPOSURE
# =============================================================================
def test_boundary_max_portfolio_exposure(firewall, valid_intent, valid_balances, valid_risk_state, valid_ticker):
    # Existing portfolio is $46,000. New order is $6,000 -> $52,000 > max $50,000
    existing_pos = {
        "ETHUSDT": Position(
            symbol="ETHUSDT", direction=1, size=15.0, entry_price=3000.0, mark_price=3066.67
        )
    }
    dec = firewall.evaluate_order_intent(valid_intent, existing_pos, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "MAX_PORTFOLIO_EXPOSURE_BREACH"


# =============================================================================
# 21. GROSS LEVERAGE LIMIT
# =============================================================================
def test_boundary_leverage_limit(firewall, valid_intent, valid_balances, valid_ticker):
    # Equity is only $2,500. Order is $6,000 -> 2.4x leverage > max 2.0x
    low_equity_state = RiskState(equity=2500.0, peak_equity=2500.0, drawdown_pct=0.0)
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, low_equity_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "LEVERAGE_LIMIT_BREACH"


# =============================================================================
# 22. ASSET CONCENTRATION LIMIT
# =============================================================================
def test_boundary_concentration_limit(firewall, valid_intent, valid_balances, valid_ticker):
    # Equity is $10,000. Order is $6,000 (60% concentration > max 35%)
    eq_state = RiskState(equity=10000.0, peak_equity=10000.0, drawdown_pct=0.0)
    dec = firewall.evaluate_order_intent(valid_intent, {}, valid_balances, eq_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "CONCENTRATION_LIMIT_BREACH"


# =============================================================================
# FAIL-CLOSED INVARIANT TEST
# =============================================================================
def test_fail_closed_on_corrupt_intent(firewall, valid_balances, valid_risk_state, valid_ticker):
    # Pass an object that causes an exception inside the evaluate loop
    corrupted_intent = "not_an_intent_object"
    dec = firewall.evaluate_order_intent(corrupted_intent, {}, valid_balances, valid_risk_state, valid_ticker)
    assert dec.approved is False
    assert dec.rule_code == "FAIL_CLOSED"
