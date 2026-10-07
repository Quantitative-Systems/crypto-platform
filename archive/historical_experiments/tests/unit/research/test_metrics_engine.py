"""
Unit Tests for Product 04: Metrics Engine & Edge States
"""

import pytest
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.metrics.metrics_engine import MetricsEngine
from research.metrics.exit_attribution import ExitAttributionEngine
from research.analytics.failure_analyzer import FailureAnalyzer


def test_empty_trades_edge_states():
    ledger = TradeLedger(initial_equity=10000.0)
    metrics = MetricsEngine.calculate_metrics([], ledger)

    assert metrics["total_trades"] == 0
    assert metrics["profit_factor"] == "NOT_AVAILABLE"
    assert metrics["expectancy_usd"] == "NOT_AVAILABLE"
    assert metrics["expectancy_r"] == "NOT_AVAILABLE"
    assert metrics["sharpe_ratio"] == "NOT_AVAILABLE"
    assert metrics["sortino_ratio"] == "NOT_AVAILABLE"
    assert metrics["max_drawdown_pct"] == 0.0


def test_zero_losses_infinite_profit_factor():
    ledger = TradeLedger(initial_equity=10000.0)
    winning_trade = SimulatedTrade(
        trade_id="t1",
        hypothesis_id="HYP_A",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        status="CLOSED",
        realized_pnl=500.0,
        realized_rr=5.0,
        dollar_risk=100.0,
        exit_reason="HTF_TP"
    )
    metrics = MetricsEngine.calculate_metrics([winning_trade], ledger)

    assert metrics["total_trades"] == 1
    assert metrics["win_rate"] == 1.0
    assert metrics["loss_rate"] == 0.0
    assert metrics["profit_factor"] == "INFINITE"
    assert metrics["expectancy_usd"] == 500.0
    assert metrics["expectancy_r"] == 5.0


def test_expectancy_and_attribution():
    ledger = TradeLedger(initial_equity=10000.0)
    t1 = SimulatedTrade(
        trade_id="t1", hypothesis_id="HYP_A", symbol="BTCUSDT", timeframe_set="SET_4",
        directional_permission="PERMIT_LONG", setup_timestamp=1000, status="CLOSED",
        realized_pnl=400.0, realized_rr=4.0, dollar_risk=100.0, exit_reason="HTF_TP"
    )
    t2 = SimulatedTrade(
        trade_id="t2", hypothesis_id="HYP_A", symbol="BTCUSDT", timeframe_set="SET_4",
        directional_permission="PERMIT_LONG", setup_timestamp=2000, status="CLOSED",
        realized_pnl=-100.0, realized_rr=-1.0, dollar_risk=100.0, exit_reason="INITIAL_LTF_SL"
    )
    t3 = SimulatedTrade(
        trade_id="t3", hypothesis_id="HYP_B", symbol="BTCUSDT", timeframe_set="SET_4",
        directional_permission="PERMIT_SHORT", setup_timestamp=3000, status="CLOSED",
        realized_pnl=150.0, realized_rr=1.5, dollar_risk=100.0, exit_reason="MTF_STRUCTURAL_TRAIL"
    )

    trades = [t1, t2, t3]
    metrics = MetricsEngine.calculate_metrics(trades, ledger)

    assert metrics["total_trades"] == 3
    assert metrics["win_count"] == 2
    assert metrics["loss_count"] == 1
    assert metrics["gross_profit_usd"] == 550.0
    assert metrics["gross_loss_usd"] == 100.0
    assert metrics["profit_factor"] == 5.5

    # Exit attribution
    attribution = ExitAttributionEngine.analyze(trades)
    assert attribution["HTF_TP"]["trade_count"] == 1
    assert attribution["HTF_TP"]["win_rate"] == 1.0
    assert attribution["INITIAL_LTF_SL"]["trade_count"] == 1
    assert attribution["INITIAL_LTF_SL"]["win_rate"] == 0.0
    assert attribution["MTF_STRUCTURAL_TRAIL"]["trade_count"] == 1
    assert attribution["MTF_STRUCTURAL_TRAIL"]["win_rate"] == 1.0

    # Failure mode analysis
    failures = FailureAnalyzer.classify_failure_modes(trades)
    assert failures["total_losing_trades"] == 1
    assert failures["failure_mode_breakdown"]["INITIAL_STRUCTURAL_INVALIDATION"]["count"] == 1
