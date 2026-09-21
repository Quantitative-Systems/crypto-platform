"""
Unit tests for QCP Paper Execution Engine, Execution Telemetry, and Forward Qualification.

S1 REMEDIATION TESTS — EABG-001:
  - Verify ExecutionTelemetryLogger requires explicit environment + session_id (fail-closed).
  - Verify TradeTelemetryRecord requires environment + session_id fields.
  - Verify environment mismatch between record and logger is rejected.
  - Verify TEST environment writes to caller-supplied temp dir (never forward path).
  - Verify forward paper factory writes to FORWARD_PAPER environment.
  - Verify no defaults exist that could cause contamination.
"""

import os
import uuid
import json
import pytest
import tempfile

from platform_core.canonical_strategy_spec import create_fam07_spec, StrategyLifecycleState
from production.telemetry.execution_telemetry import (
    ExecutionTelemetryLogger,
    TradeTelemetryRecord,
    PERMITTED_ENVIRONMENTS,
    write_contamination_manifest,
)
from production.qualification.forward_qualification_engine import (
    ForwardQualificationEngine,
    QualificationStatus,
)
from production.paper_execution_harness import PaperExecutionHarness


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_record(
    trade_id="TRADE_001",
    environment="TEST",
    session_id=None,
    net_r=2.44,
) -> TradeTelemetryRecord:
    """Build a minimal but valid TradeTelemetryRecord for testing."""
    return TradeTelemetryRecord(
        environment=environment,
        session_id=session_id or str(uuid.uuid4()),
        trade_id=trade_id,
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
        net_r=net_r,
        market_regime="BULL_CONTINUATION",
        peak_unrealized_r=2.5,
        max_adverse_r=0.1,
        portfolio_heat_at_entry_pct=0.60,
        breakeven_triggered=True,
    )


# ─── S1: Fail-closed construction tests ───────────────────────────────────────

class TestTelemetryLoggerS1FailClosed:
    """S1 — EABG-001: Verify ExecutionTelemetryLogger fails closed without provenance."""

    def test_no_log_dir_raises(self, tmp_path):
        """Logger must reject empty log_dir."""
        with pytest.raises((RuntimeError, TypeError)):
            ExecutionTelemetryLogger(
                log_dir="",
                environment="TEST",
                session_id=str(uuid.uuid4()),
            )

    def test_missing_environment_raises(self, tmp_path):
        """Logger must reject missing or invalid environment."""
        with pytest.raises((RuntimeError, ValueError)):
            ExecutionTelemetryLogger(
                log_dir=str(tmp_path),
                environment="",
                session_id=str(uuid.uuid4()),
            )

    def test_invalid_environment_raises(self, tmp_path):
        """Logger must reject unknown environment strings."""
        with pytest.raises((RuntimeError, ValueError)):
            ExecutionTelemetryLogger(
                log_dir=str(tmp_path),
                environment="PRODUCTION",   # not a permitted value
                session_id=str(uuid.uuid4()),
            )

    def test_missing_session_id_raises(self, tmp_path):
        """Logger must reject empty session_id."""
        with pytest.raises((RuntimeError, ValueError)):
            ExecutionTelemetryLogger(
                log_dir=str(tmp_path),
                environment="TEST",
                session_id="",
            )

    def test_permitted_environments_coverage(self, tmp_path):
        """All permitted environments must construct successfully."""
        for env in PERMITTED_ENVIRONMENTS:
            logger = ExecutionTelemetryLogger(
                log_dir=str(tmp_path / env),
                environment=env,
                session_id=str(uuid.uuid4()),
            )
            assert logger.environment == env

    def test_for_test_factory(self, tmp_path):
        """for_test factory sets environment=TEST."""
        logger = ExecutionTelemetryLogger.for_test(log_dir=str(tmp_path))
        assert logger.environment == "TEST"
        assert logger.session_id  # non-empty

    def test_for_forward_paper_factory(self, tmp_path):
        """for_forward_paper factory sets environment=FORWARD_PAPER."""
        logger = ExecutionTelemetryLogger.for_forward_paper(log_dir=str(tmp_path))
        assert logger.environment == "FORWARD_PAPER"
        assert logger.session_id

    def test_for_research_factory(self, tmp_path):
        """for_research factory sets environment=RESEARCH."""
        logger = ExecutionTelemetryLogger.for_research(log_dir=str(tmp_path))
        assert logger.environment == "RESEARCH"


# ─── S1: Record provenance enforcement tests ──────────────────────────────────

class TestTradeTelemetryRecordS1Provenance:
    """S1 — EABG-001: Verify TradeTelemetryRecord enforces provenance fields."""

    def test_valid_record_constructs(self):
        rec = _make_record(environment="TEST")
        assert rec.environment == "TEST"

    def test_invalid_environment_raises(self):
        with pytest.raises(ValueError):
            _make_record(environment="LIVE_TRADING")  # not permitted

    def test_empty_environment_raises(self):
        with pytest.raises(ValueError):
            _make_record(environment="")

    def test_empty_session_id_raises(self):
        with pytest.raises((ValueError, TypeError)):
            _make_record(session_id=" ")  # whitespace-only should be treated as invalid

    def test_record_to_dict_contains_provenance(self):
        rec = _make_record(environment="RESEARCH")
        d = rec.to_dict()
        assert "environment" in d
        assert "session_id" in d
        assert d["environment"] == "RESEARCH"


# ─── S1: Environment isolation enforcement tests ───────────────────────────────

class TestEnvironmentIsolation:
    """S1 — Verify environment mismatch between logger and record is rejected."""

    def test_matching_env_accepted(self, tmp_path):
        session = str(uuid.uuid4())
        logger = ExecutionTelemetryLogger.for_test(str(tmp_path), session_id=session)
        rec = _make_record(environment="TEST", session_id=session)
        logger.record_trade(rec)  # must not raise
        assert len(logger.records) == 1

    def test_mismatched_environment_rejected(self, tmp_path):
        session = str(uuid.uuid4())
        logger = ExecutionTelemetryLogger.for_test(str(tmp_path), session_id=session)
        # Record claims RESEARCH but logger is TEST
        rec = _make_record(environment="RESEARCH", session_id=session)
        with pytest.raises(ValueError, match="environment"):
            logger.record_trade(rec)

    def test_mismatched_session_id_rejected(self, tmp_path):
        logger = ExecutionTelemetryLogger.for_test(str(tmp_path), session_id=str(uuid.uuid4()))
        # Record has different session_id
        rec = _make_record(environment="TEST", session_id=str(uuid.uuid4()))
        with pytest.raises(ValueError, match="session_id"):
            logger.record_trade(rec)

    def test_summary_metrics_contain_provenance(self, tmp_path):
        session = str(uuid.uuid4())
        logger = ExecutionTelemetryLogger.for_test(str(tmp_path), session_id=session)
        rec = _make_record(environment="TEST", session_id=session)
        logger.record_trade(rec)
        summary = logger.get_summary_metrics()
        assert summary["environment"] == "TEST"
        assert summary["session_id"] == session


# ─── S1: Full telemetry logging test (updated for new API) ────────────────────

def test_execution_telemetry_logging(tmp_path):
    """Updated S1-compliant telemetry logging test."""
    log_dir = str(tmp_path / "telemetry")
    session = str(uuid.uuid4())
    logger = ExecutionTelemetryLogger.for_test(log_dir=log_dir, session_id=session)

    record = _make_record(environment="TEST", session_id=session, net_r=2.44)
    logger.record_trade(record)
    assert len(logger.records) == 1

    summary = logger.get_summary_metrics()
    assert summary["total_trades"] == 1
    assert summary["winning_trades"] == 1
    assert summary["net_r"] == 2.44

    # Verify JSONL file persistence — record must carry provenance fields
    assert os.path.exists(logger.log_file)
    with open(logger.log_file, "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["trade_id"] == "TRADE_001"
        assert data["environment"] == "TEST"
        assert data["session_id"] == session


# ─── S1: Contamination manifest test ──────────────────────────────────────────

def test_contamination_manifest_written(tmp_path):
    """write_contamination_manifest must produce a valid JSON manifest."""
    manifest_path = write_contamination_manifest(
        log_dir=str(tmp_path),
        total_rows=2302,
        unique_rows=1074,
        max_repetition=20,
        audit_timestamp_utc="2026-09-17T12:00:00+00:00",
        first_trade_id="POS_FAM-07-MTFCONT_SOLUSDT_Set2_1704110400",
    )
    assert os.path.exists(manifest_path)
    with open(manifest_path) as f:
        m = json.load(f)
    assert m["total_rows"] == 2302
    assert m["unique_trade_ids"] == 1074
    assert m["duplicate_rows"] == 1228
    assert m["admissibility"] == "NON_EVIDENCE_CONTAMINATED_SOURCE"
    assert m["verdict"] == "FAIL_CONTAMINATED_NON_EVIDENCE"


# ─── FAM-07 spec: verify F-04 fix (no fiat lifecycle default) ─────────────────

def test_create_fam07_spec_defaults_to_research():
    """F-04 fix: create_fam07_spec must default to RESEARCH, not QUALIFIED_ROBUST."""
    spec = create_fam07_spec()
    assert spec.lifecycle_state == StrategyLifecycleState.RESEARCH, (
        f"Expected RESEARCH but got {spec.lifecycle_state}. "
        "F-04 fix: factory must not fiat-assign a promoted lifecycle state."
    )


def test_create_fam07_spec_explicit_state_accepted():
    """Explicit lifecycle state overrides the RESEARCH default."""
    spec = create_fam07_spec(lifecycle_state=StrategyLifecycleState.PROMISING)
    assert spec.lifecycle_state == StrategyLifecycleState.PROMISING


# ─── Forward qualification engine tests (unchanged) ───────────────────────────

def test_forward_qualification_engine():
    strat_id = "FAM-07-MTFCONT_SOLUSDT_Set2"

    # Scenario 1: Insufficient data (< 15 trades)
    trades_insufficient = [{"net_r": 0.5} for _ in range(5)]
    rep = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_insufficient)
    assert rep.status == QualificationStatus.INSUFFICIENT_DATA

    # Scenario 2: Healthy performance (20 trades with ~0.4R expectancy and 40% win rate)
    trades_healthy = [{"net_r": 2.0} for _ in range(8)] + [{"net_r": -1.0} for _ in range(12)]
    rep_healthy = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_healthy)
    assert rep_healthy.status == QualificationStatus.FORWARD_HEALTHY
    assert rep_healthy.realized_net_r == 4.0

    # Scenario 3: Degraded performance (all losses, negative expectancy)
    trades_degraded = [{"net_r": -1.0} for _ in range(20)]
    rep_degraded = ForwardQualificationEngine.evaluate_candidate_telemetry(strat_id, trades_degraded)
    assert rep_degraded.status == QualificationStatus.DEGRADATION_DETECTED
    assert rep_degraded.recommendation == "PAUSE_AND_QUARANTINE"


# ─── Paper harness isolation test ─────────────────────────────────────────────

def test_paper_harness_uses_simulation_dir(tmp_path):
    """
    S1: Non-forward paper harness must write telemetry to the simulations subdirectory,
    not the canonical forward paper directory.
    """
    state_file = str(tmp_path / "test_paper_state.json")
    sim_telem_dir = str(tmp_path / "sim_telemetry")
    spec = create_fam07_spec(symbol="SOL/USDT", timeframe_set=2)
    audit_file = str(tmp_path / "test_paper_audit.json")

    harness = PaperExecutionHarness(
        starting_capital=1000.0,
        specs=[spec],
        state_file=state_file,
        audit_file=audit_file,
        telemetry_dir=sim_telem_dir,  # explicit isolation
        is_forward_daemon=False,
    )

    # S1 invariant: environment must be RESEARCH (not FORWARD_PAPER)
    assert harness.environment == "RESEARCH", (
        f"Expected RESEARCH but got {harness.environment}. "
        "Non-forward harness must not write to FORWARD_PAPER."
    )
    assert harness.session_id  # non-empty UUID
    assert harness.telemetry.environment == "RESEARCH"


def test_paper_harness_short_window(tmp_path):
    """Paper harness runs a short window without raising."""
    state_file = str(tmp_path / "test_paper_state.json")
    spec = create_fam07_spec(symbol="SOL/USDT", timeframe_set=2)
    audit_file = str(tmp_path / "test_paper_audit.json")
    telem_dir = str(tmp_path / "telemetry")

    harness = PaperExecutionHarness(
        starting_capital=1000.0,
        specs=[spec],
        state_file=state_file,
        audit_file=audit_file,
        telemetry_dir=telem_dir,
    )

    # Run over a 10-day slice in 2024
    start_ts = 1704067200          # 2024-01-01
    end_ts = start_ts + 10 * 86400  # 10 days later

    result = harness.run_forward_paper_simulation(start_ts=start_ts, end_ts=end_ts, audit_file=audit_file)
    assert result["platform"] == "Quantitative Crypto Platform (QCP)"
    assert os.path.exists(state_file)
    assert harness.last_processed_timestamp >= start_ts
