"""Unit tests for STRATA Automated Circuit Breakers & Capital Protection."""
import time
import pytest
from execution.risk.circuit_breakers import (
    BreakerStatus,
    CompositeCircuitBreakerManager,
    ConsecutiveLossBreaker,
    MaxDrawdownBreaker,
    ReconciliationDiscrepancyBreaker,
    StaleDataBreaker,
)


def test_max_drawdown_breaker_trips():
    breaker = MaxDrawdownBreaker(max_drawdown_pct=0.04)

    # 2% drawdown -> safe
    res = breaker.evaluate({"current_equity_usd": 98_000.0, "peak_equity_usd": 100_000.0})
    assert res.is_safe
    assert res.status == BreakerStatus.ARMED

    # 5% drawdown -> trips
    res = breaker.evaluate({"current_equity_usd": 95_000.0, "peak_equity_usd": 100_000.0})
    assert not res.is_safe
    assert res.status == BreakerStatus.TRIPPED
    assert res.reason_code == "CIRCUIT_BREAKER_MAX_DRAWDOWN"


def test_consecutive_loss_breaker_trips():
    breaker = ConsecutiveLossBreaker(max_consecutive_losses=3, cooldown_seconds=100)

    # 2 losses -> safe
    res = breaker.evaluate({"consecutive_losses": 2})
    assert res.is_safe

    # 3 losses -> trips
    res = breaker.evaluate({"consecutive_losses": 3})
    assert not res.is_safe
    assert res.status == BreakerStatus.TRIPPED
    assert res.reason_code == "CIRCUIT_BREAKER_CONSECUTIVE_LOSS"


def test_stale_data_breaker_trips():
    breaker = StaleDataBreaker(max_stale_seconds=30.0)
    now_ms = int(time.time() * 1000)

    # 10s old -> safe
    res = breaker.evaluate({"last_tick_timestamp_ms": now_ms - 10000})
    assert res.is_safe

    # 45s old -> trips
    res = breaker.evaluate({"last_tick_timestamp_ms": now_ms - 45000})
    assert not res.is_safe
    assert res.status == BreakerStatus.TRIPPED


def test_composite_breaker_blocks_trading_on_any_failure():
    mgr = CompositeCircuitBreakerManager()
    ctx = {
        "current_equity_usd": 90_000.0,  # 10% DD
        "peak_equity_usd": 100_000.0,
        "consecutive_losses": 0,
        "last_tick_timestamp_ms": int(time.time() * 1000),
        "reconciliation_discrepancy_count": 0,
    }
    all_safe, reasons, states = mgr.evaluate_all(ctx)
    assert not all_safe
    assert "CIRCUIT_BREAKER_MAX_DRAWDOWN" in reasons
