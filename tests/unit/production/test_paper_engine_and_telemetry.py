"""
Unit tests for QCP Paper Execution Engine, Execution Telemetry, and Forward Qualification.
"""

import os
import pytest
import tempfile
import json

from platform_core.canonical_strategy_spec import create_fam07_spec, StrategyLifecycleState
from production.telemetry.execution_telemetry import (
    ExecutionTelemetryLogger,
    TradeTelemetryRecord,
)
from production.qualification.forward_qualification_engine import (
    ForwardQualificationEngine,
    QualificationStatus,
)
from production.paper_execution_harness import PaperExecutionHarness


def test_execution_telemetry_logging(tmp_path):
    log_dir = str(tmp_path / "telemetry")
    logger = ExecutionTelemetryLogger(log_dir=log_dir)

    record = TradeTelemetryRecord(
        trade_id="TRADE_001",
        strategy_id="FAM-07-MTFCONT_SOLUSDT_Set2",
        symbol="SOLUSDT",
        timeframe_set=2,
        direction="BUY",
        entry_timestamp=1704110400,
        exit_timestamp=1704124800,
        holding_bars=1,
        holding_seconds=14400,
        expected_entry_price=100.0,
        executed_entry_price=100.0,
        entry_slippage_bps=0.0,
        entry_fee_usd=0.02,
        expected_exit_price=105.0,
        executed_exit_price=104.95,
        exit_slippage_bps=5.0,
        exit_fee_usd=0.05,
        position_units=1.0,
        position_notional_usd=100.0,
        initial_risk_usd=2.0,
        exit_reason="TP_HIT",
        gross_pnl_usd=4.95,
        total_friction_usd=0.07,
        net_pnl_usd=4.88,
        gross_r=2.475,
        friction_r=0.035,
        net_r=2.44,
        market_regime="BULL_CONTINUATION",
        peak_unrealized_r=2.5,
        max_adverse_r=0.1,
        portfolio_heat_at_entry_pct=0.60,
        breakeven_triggered=True,
    )

    logger.record_trade(record)
    assert len(logger.records) == 1

    summary = logger.get_summary_metrics()
    assert summary["total_trades"] == 1
    assert summary["winning_trades"] == 1
    assert summary["net_r"] == 2.44

    # Verify JSONL file persistence
    assert os.path.exists(logger.log_file)
    with open(logger.log_file, "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["trade_id"] == "TRADE_001"


def test_forward_qualification_engine():
    strat_id = "FAM-07-MTFCONT_SOLUSDT_Set2"

    # Scenario 1: Insufficient data (< 15 trades)
    trades_insufficient = [{"net_r": 0.5} for _ in range(5)]
    rep = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_insufficient)
    assert rep.status == QualificationStatus.INSUFFICIENT_DATA

    # Scenario 2: Healthy performance (20 trades with ~0.4R expectancy and 40% win rate)
    trades_healthy = [{"net_r": 2.0} for _ in range(8)] + [{"net_r": -1.0} for _ in range(12)]
    # total net_r = 16 - 12 = 4.0R, exp_r = 0.20R, wr = 40%
    rep_healthy = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_healthy)
    assert rep_healthy.status == QualificationStatus.FORWARD_HEALTHY
    assert rep_healthy.realized_net_r == 4.0

    # Scenario 3: Degraded performance (all losses, negative expectancy)
    trades_degraded = [{"net_r": -1.0} for _ in range(20)]
    rep_degraded = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_degraded)
    assert rep_degraded.status == QualificationStatus.DEGRADATION_DETECTED
    assert rep_degraded.recommendation == "PAUSE_AND_QUARANTINE"


def test_paper_execution_harness_short_window(tmp_path):
    state_file = str(tmp_path / "test_paper_state.json")
    spec = create_fam07_spec(
        symbol="SOL/USDT",
        timeframe_set=2,
        lifecycle_state=StrategyLifecycleState.QUALIFIED_ROBUST,
    )
    audit_file = str(tmp_path / "test_paper_audit.json")
    harness = PaperExecutionHarness(
        starting_capital=1000.0,
        specs=[spec],
        state_file=state_file,
        audit_file=audit_file,
    )

    # Run over a 10-day slice in 2024
    start_ts = 1704067200         # 2024-01-01
    end_ts = start_ts + 10 * 86400 # 10 days later

    result = harness.run_forward_paper_simulation(start_ts=start_ts, end_ts=end_ts, audit_file=audit_file)
    assert result["platform"] == "Quantitative Crypto Platform (QCP)"
    assert os.path.exists(state_file)
    assert harness.last_processed_timestamp >= start_ts
