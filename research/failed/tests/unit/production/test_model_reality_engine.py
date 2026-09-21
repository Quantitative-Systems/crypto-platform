"""
Unit tests for QCP Model-vs-Reality (Execution Reality Delta) Engine.
Tests execution slippage error, friction model error, R-realization delta,
rolling expectancy decay, and automated reality gap alerts.
"""

import pytest
from production.qualification.model_reality_engine import (
    ModelVsRealityEngine,
    TradeRealityDelta,
    ModelRealitySummary,
)


def test_evaluate_trade_delta():
    trade = {
        "trade_id": "TRADE_001",
        "symbol": "SOLUSDT",
        "direction": "BUY",
        "expected_entry_price": 100.0,
        "observed_market_price": 100.0,
        "executed_entry_price": 100.02,
        "entry_slippage_bps": 2.0,
        "exit_slippage_bps": 6.0,
        "position_notional_usd": 1000.0,
        "total_friction_usd": 1.50,  # 15 bps observed
        "gross_r": 2.50,
        "net_r": 2.35,
        "holding_seconds": 14400,
    }

    delta = ModelVsRealityEngine.evaluate_trade(
        trade,
        expected_entry_slippage_bps=2.0,
        expected_exit_slippage_bps=5.0,
        expected_entry_fee_bps=2.0,
        expected_exit_fee_bps=5.0,
    )

    assert delta.trade_id == "TRADE_001"
    # Expected slippage = 2 + 5 = 7 bps; Observed slippage = 2 + 6 = 8 bps -> error = +1 bps
    assert delta.observed_slippage_bps == 8.0
    assert delta.expected_slippage_bps == 7.0
    assert delta.slippage_model_error_bps == 1.0

    # Observed friction = 1.50 / 1000 * 10000 = 15.0 bps; Expected = 7 + 2 + 5 = 14.0 bps -> error = +1.0 bps
    assert abs(delta.observed_friction_bps - 15.0) < 1e-4
    assert abs(delta.expected_friction_bps - 14.0) < 1e-4
    assert abs(delta.friction_model_error_bps - 1.0) < 1e-4

    # R realization delta = 2.35 - 2.50 = -0.15R
    assert abs(delta.r_realization_delta - (-0.15)) < 1e-4


def test_audit_reality_gap_nominal():
    # 20 trades matching +0.61R expectancy
    trades = [
        {
            "trade_id": f"T_{i}",
            "position_notional_usd": 500.0,
            "entry_slippage_bps": 2.0,
            "exit_slippage_bps": 5.0,
            "total_friction_usd": 0.70,  # 14 bps
            "gross_r": 0.75,
            "net_r": 0.61,
        }
        for i in range(20)
    ]

    summary = ModelVsRealityEngine.audit_reality_gap(
        trades,
        backtest_expectancy_r=0.61,
        backtest_win_rate=1.0,
    )

    assert summary.total_trades_analyzed == 20
    assert abs(summary.avg_slippage_error_bps) < 1e-4
    assert abs(summary.avg_friction_error_bps) < 1e-4
    assert abs(summary.expectancy_decay_pct) < 1.0
    assert len(summary.alerts) == 0


def test_friction_model_underestimate_alert():
    # Observed friction is 20 bps while expected is 14 bps (error = +6 bps > 3.0 bps threshold)
    trades = [
        {
            "trade_id": f"T_{i}",
            "position_notional_usd": 500.0,
            "entry_slippage_bps": 2.0,
            "exit_slippage_bps": 5.0,
            "total_friction_usd": 1.00,  # 20 bps
            "gross_r": 0.75,
            "net_r": 0.61,
        }
        for i in range(10)
    ]

    summary = ModelVsRealityEngine.audit_reality_gap(trades, backtest_expectancy_r=0.61)
    assert any("FRICTION_MODEL_UNDERESTIMATING_COST" in a for a in summary.alerts)


def test_alpha_decay_alert():
    # Forward expectancy is +0.30R vs backtest +0.61R (-50.8% decay < -30% threshold)
    trades = [
        {
            "trade_id": f"T_{i}",
            "position_notional_usd": 500.0,
            "entry_slippage_bps": 2.0,
            "exit_slippage_bps": 5.0,
            "total_friction_usd": 0.70,
            "gross_r": 0.44,
            "net_r": 0.30,
        }
        for i in range(10)
    ]

    summary = ModelVsRealityEngine.audit_reality_gap(trades, backtest_expectancy_r=0.61)
    assert any("SUBSTANTIAL_ALPHA_DECAY" in a for a in summary.alerts)
    assert summary.expectancy_decay_pct < -30.0
