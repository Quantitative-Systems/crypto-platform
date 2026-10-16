"""Unit tests for Crypto Engine Phase 5: Multi-Account Portfolio Risk Governor."""
from __future__ import annotations

import pytest

from execution.portfolio.multi_account_portfolio_governor import (
    MultiAccountPortfolioGovernor,
    build_default_strata_multi_account_portfolio,
)


def test_fail_closed_live_capital_assertion():
    """Asserts that attempting to authorize live capital raises a RuntimeError."""
    with pytest.raises(RuntimeError, match="Live capital authorization must remain at \\$0.00"):
        MultiAccountPortfolioGovernor(live_capital_authorized=10_000.0)


def test_sub_account_registration_and_status():
    """Asserts that sub-accounts initialize with correct balances and zero heat."""
    gov = build_default_strata_multi_account_portfolio()
    status = gov.get_portfolio_status()

    assert status.total_equity_usd == 1_000_000.0
    assert status.total_active_positions == 0
    assert status.aggregate_risk_heat_pct == 0.0
    assert status.available_risk_headroom_pct == 3.0
    assert not status.is_global_circuit_breaker_active
    assert len(status.sub_account_summaries) == 3


def test_multi_style_routing_and_allocation():
    """Asserts that candidates are routed to the sub-account matching their style mandate."""
    gov = build_default_strata_multi_account_portfolio()

    # Investing candidate -> routes to ACC_MACRO_TREND
    cand_inv = {"symbol": "BTCUSDT", "style": "INVESTING", "risk_pct": 0.01}
    approved, reason, acc_id = gov.request_position_allocation(cand_inv, current_time_ms=1000)
    assert approved is True
    assert acc_id == "ACC_MACRO_TREND"

    # Register position opened
    gov.register_position_opened("ACC_MACRO_TREND", "TRD_001", cand_inv)
    assert gov.total_active_positions == 1
    assert round(gov.total_aggregate_heat_pct, 4) == 0.01

    # Swing candidate -> routes to ACC_TACTICAL_SWING
    cand_swg = {"symbol": "ETHUSDT", "style": "SWING", "risk_pct": 0.01}
    approved, reason, acc_id = gov.request_position_allocation(cand_swg, current_time_ms=1000)
    assert approved is True
    assert acc_id == "ACC_TACTICAL_SWING"

    gov.register_position_opened("ACC_TACTICAL_SWING", "TRD_002", cand_swg)
    assert gov.total_active_positions == 2
    assert round(gov.total_aggregate_heat_pct, 4) == 0.02

    # Scalp candidate -> routes to ACC_MOMENTUM_REACT
    cand_scl = {"symbol": "SOLUSDT", "style": "SCALP", "risk_pct": 0.01}
    approved, reason, acc_id = gov.request_position_allocation(cand_scl, current_time_ms=1000)
    assert approved is True
    assert acc_id == "ACC_MOMENTUM_REACT"

    gov.register_position_opened("ACC_MOMENTUM_REACT", "TRD_003", cand_scl)
    assert gov.total_active_positions == 3
    assert round(gov.total_aggregate_heat_pct, 4) == 0.03


def test_global_concurrency_and_heat_limits():
    """Asserts that candidate entries beyond 3 positions or 3% heat are rejected."""
    gov = build_default_strata_multi_account_portfolio()

    # Fill all 3 slots across the 3 sub-accounts
    test_signals = [
        {"symbol": "BTCUSDT", "style": "INVESTING", "risk_pct": 0.01},
        {"symbol": "ETHUSDT", "style": "SWING", "risk_pct": 0.01},
        {"symbol": "SOLUSDT", "style": "SCALP", "risk_pct": 0.01},
    ]

    for i, cand in enumerate(test_signals):
        appr, _, acc_id = gov.request_position_allocation(cand, 1000)
        assert appr is True
        gov.register_position_opened(acc_id, f"TRD_{i}", cand)

    # 4th candidate must be suppressed by portfolio cap
    cand_4 = {"symbol": "BNBUSDT", "style": "INVESTING", "risk_pct": 0.01}
    approved, reason, _ = gov.request_position_allocation(cand_4, 1000)
    assert approved is False
    assert "SUPPRESSED_PORTFOLIO_CAP" in reason


def test_global_daily_drawdown_circuit_breaker():
    """Asserts that experiencing >= 3.0% aggregate daily drawdown halts all trading."""
    gov = build_default_strata_multi_account_portfolio()
    # Initial equity: 1,000,000 USD. 3% is 30,000 USD loss.
    # Open and close losing trades in Macro Trend (500k allocation, 1% risk = 5000 USD/R)
    cand = {"symbol": "BTCUSDT", "style": "INVESTING", "risk_pct": 0.01}
    gov.request_position_allocation(cand, current_time_ms=1000)
    gov.register_position_opened("ACC_MACRO_TREND", "TRD_LOSS", cand)

    # Realize a -6.5R loss (-32,500 USD loss = -3.25% of total 1M portfolio)
    gov.register_position_closed("ACC_MACRO_TREND", "TRD_LOSS", realized_r=-6.5, timestamp_ms=2000)

    # Check status
    status = gov.get_portfolio_status()
    assert status.is_global_circuit_breaker_active is True
    assert "GLOBAL_CIRCUIT_BREAKER" in (status.circuit_breaker_reason or "")

    # New trade request must be rejected by circuit breaker
    new_cand = {"symbol": "ETHUSDT", "style": "SWING", "risk_pct": 0.01}
    approved, reason, _ = gov.request_position_allocation(new_cand, current_time_ms=3000)
    assert approved is False
    assert "SUPPRESSED_BY_GLOBAL_CIRCUIT_BREAKER" in reason
