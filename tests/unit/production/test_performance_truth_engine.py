"""
Unit tests for QCP Performance Truth Engine.
Tests forensic audit calculations, drawdown tracking, risk-adjusted metrics,
tail risk distributions, friction drag, and dual-source reconciliation.
"""

import pytest
import numpy as np
from production.qualification.performance_truth_engine import (
    PerformanceTruthEngine,
    DrawdownMetrics,
    RiskAdjustedMetrics,
    TailRiskMetrics,
    FrictionMetrics,
    ComprehensivePerformanceAudit,
)


def test_audit_empty_trades():
    audit = PerformanceTruthEngine.audit_trades([], starting_capital=1000.0)
    assert audit.starting_capital_usd == 1000.0
    assert audit.ending_equity_usd == 1000.0
    assert audit.total_trades == 0
    assert audit.drawdown.max_drawdown_pct == 0.0
    assert audit.drawdown.max_drawdown_usd == 0.0
    assert audit.total_net_r == 0.0


def test_drawdown_detection_and_tracking():
    """
    Simulate an equity path:
    Start: $1000
    Trade 1: +$500  -> Equity = $1500 (Peak = $1500)
    Trade 2: -$300  -> Equity = $1200 (Peak = $1500, DD = $300, DD% = 20.0%)
    Trade 3: +$600  -> Equity = $1800 (Peak = $1800, New Peak, DD = 0)
    Trade 4: -$180  -> Equity = $1620 (Peak = $1800, DD = $180, DD% = 10.0%)
    Trade 5: +$380  -> Equity = $2000 (Peak = $2000, New Peak, Final Equity = $2000)

    Notice: Final equity ends AT PEAK ($2000).
    A naive (peak - final)/peak calculation would report 0.00% drawdown!
    The Performance Truth Engine MUST detect the historical max drawdown of 20.0% ($300).
    """
    trades = [
        {"net_pnl_usd": 500.0, "net_r": 2.5, "entry_fee_usd": 0.1, "exit_fee_usd": 0.1, "total_friction_usd": 0.2, "friction_r": 0.01},
        {"net_pnl_usd": -300.0, "net_r": -1.5, "entry_fee_usd": 0.1, "exit_fee_usd": 0.1, "total_friction_usd": 0.2, "friction_r": 0.01},
        {"net_pnl_usd": 600.0, "net_r": 3.0, "entry_fee_usd": 0.1, "exit_fee_usd": 0.1, "total_friction_usd": 0.2, "friction_r": 0.01},
        {"net_pnl_usd": -180.0, "net_r": -0.9, "entry_fee_usd": 0.1, "exit_fee_usd": 0.1, "total_friction_usd": 0.2, "friction_r": 0.01},
        {"net_pnl_usd": 380.0, "net_r": 1.9, "entry_fee_usd": 0.1, "exit_fee_usd": 0.1, "total_friction_usd": 0.2, "friction_r": 0.01},
    ]

    audit = PerformanceTruthEngine.audit_trades(trades, starting_capital=1000.0)

    assert audit.starting_capital_usd == 1000.0
    assert audit.ending_equity_usd == 2000.0
    assert audit.net_profit_usd == 1000.0
    assert audit.total_return_pct == 100.0
    assert audit.total_trades == 5
    assert audit.winning_trades == 3
    assert audit.losing_trades == 2
    assert audit.win_rate == 0.60

    # Verify Drawdown truth
    assert audit.drawdown.max_drawdown_usd == 300.0
    assert audit.drawdown.max_drawdown_pct == 20.0
    assert audit.drawdown.peak_equity_usd == 1500.0
    assert audit.drawdown.trough_equity_usd == 1200.0
    assert audit.drawdown.current_drawdown_pct == 0.0  # ended at peak

    # Verify R-accounting
    expected_net_r = 2.5 - 1.5 + 3.0 - 0.9 + 1.9
    assert abs(audit.total_net_r - expected_net_r) < 1e-4
    assert abs(audit.expectancy_r - (expected_net_r / 5)) < 1e-4

    # Verify Tail risk
    assert audit.tail_risk.worst_trade_loss_usd == -300.0
    assert audit.tail_risk.worst_trade_loss_r == -1.5
    assert audit.tail_risk.max_consecutive_losses == 1


def test_reconcile_two_sources_success():
    source_a = {
        "ending_equity_usd": 3783.56,
        "total_net_r": 222.92,
        "total_trades": 365,
        "win_rate": 0.7014,
        "profit_factor": 5.2351,
    }
    source_b = {
        "ending_equity_usd": 3783.56,
        "total_net_r": 222.92,
        "total_trades": 365,
        "win_rate": 0.7014,
        "profit_factor": 5.2351,
    }

    reconciled, discrepancies = PerformanceTruthEngine.reconcile_two_sources(source_a, source_b)
    assert reconciled is True
    assert len(discrepancies) == 0


def test_reconcile_two_sources_mismatch():
    source_a = {
        "ending_equity_usd": 3783.56,
        "total_net_r": 222.92,
        "total_trades": 365,
        "win_rate": 0.7014,
        "profit_factor": 5.2351,
    }
    source_b = {
        "ending_equity_usd": 3500.00,  # Mismatch
        "total_net_r": 222.92,
        "total_trades": 365,
        "win_rate": 0.7014,
        "profit_factor": 5.2351,
    }

    reconciled, discrepancies = PerformanceTruthEngine.reconcile_two_sources(source_a, source_b)
    assert reconciled is False
    assert len(discrepancies) == 1
    assert "Ending Equity mismatch" in discrepancies[0]
