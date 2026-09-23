"""Tests for Independent Fail-Closed Risk Firewall."""
import pytest
import time

from crypto_platform.core.domain import (
    AccountBalance,
    OrderIntent,
    Position,
    RiskState,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.risk_engine.circuit_breakers import CircuitBreakerConfig, CircuitState
from crypto_platform.risk_engine.firewall import RiskFirewall


def make_sample_intent(symbol="BTCUSDT", direction=1, size=0.1, limit_px=60_000.0, age_ms=0):
    now_ms = int(time.time() * 1000)
    return OrderIntent(
        intent_id="int_01",
        strategy_id="strat_01",
        tenant_id="t_01",
        account_id="acc_01",
        symbol=symbol,
        direction=direction,
        target_size=size,
        limit_price=limit_px,
        created_at_ms=now_ms - age_ms,
    )


def make_sample_ticker(symbol="BTCUSDT", price=60_000.0, age_ms=0):
    now_ms = int(time.time() * 1000)
    return TickerEvent(
        venue="binance",
        symbol=symbol,
        timestamp_ms=now_ms - age_ms,
        bid=price - 1.0,
        ask=price + 1.0,
        last_price=price,
    )


def test_risk_firewall_pass():
    firewall = RiskFirewall()
    intent = make_sample_intent()
    ticker = make_sample_ticker()
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is True
    assert decision.rule_code == "PASS"


def test_risk_firewall_kill_switch():
    firewall = RiskFirewall()
    firewall.kill_switches.activate("TENANT", "t_01", reason="Manual audit required")

    intent = make_sample_intent()
    ticker = make_sample_ticker()
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert "Kill Switch" in decision.reason
    assert decision.rule_code in ("KILL_SWITCH_ACTIVE", "TENANT_KILL_SWITCH_ACTIVE")


def test_risk_firewall_stale_signal():
    firewall = RiskFirewall(max_signal_age_ms=1000)
    intent = make_sample_intent(age_ms=2500)
    ticker = make_sample_ticker()
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert decision.rule_code == "STALE_SIGNAL"


def test_risk_firewall_stale_market_data():
    firewall = RiskFirewall(max_market_data_age_ms=2000)
    intent = make_sample_intent()
    ticker = make_sample_ticker(age_ms=3500)
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert decision.rule_code == "STALE_MARKET_DATA"


def test_risk_firewall_fat_finger_price():
    firewall = RiskFirewall(max_price_deviation_pct=0.03)
    # Market is 60,000; intent limit is 65,000 (>8% deviation)
    intent = make_sample_intent(limit_px=65_000.0)
    ticker = make_sample_ticker(price=60_000.0)
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert decision.rule_code == "FAT_FINGER_PRICE_DEVIATION"


def test_risk_firewall_leverage_limit():
    firewall = RiskFirewall(max_gross_leverage=1.5)
    # Equity $10,000; new order 0.5 BTC * $60,000 = $30,000 (leverage 3.0x > 1.5x)
    intent = make_sample_intent(size=0.5)
    ticker = make_sample_ticker(price=60_000.0)
    risk_state = RiskState(equity=10_000.0, peak_equity=10_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert decision.rule_code == "LEVERAGE_LIMIT_BREACH"


def test_risk_firewall_circuit_breaker_drawdown():
    cfg = CircuitBreakerConfig(daily_halt_pct=0.05)
    firewall = RiskFirewall(circuit_config=cfg)

    # Initial equity was 100k, now dropped to 94k (-6% daily loss)
    cb = firewall.get_or_create_circuit_breaker("acc_01", initial_equity=100_000.0)
    cb.update_equity(94_000.0)

    intent = make_sample_intent()
    ticker = make_sample_ticker()
    risk_state = RiskState(equity=94_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=ticker,
    )
    assert decision.approved is False
    assert decision.rule_code in ("CIRCUIT_BREAKER_TRIPPED", "DAILY_LOSS_LIMIT_BREACH")


def test_risk_firewall_fail_closed_on_corrupt_data():
    firewall = RiskFirewall()
    intent = make_sample_intent()
    # Ticker is None
    risk_state = RiskState(equity=100_000.0, peak_equity=100_000.0)

    decision = firewall.evaluate_order_intent(
        intent=intent,
        current_positions={},
        balances={},
        risk_state=risk_state,
        latest_ticker=None,
    )
    assert decision.approved is False
    assert decision.rule_code in ("MISSING_MARKET_DATA", "FAIL_CLOSED")
