"""Unit tests for Phase O Paper Execution Reconciliation and Microstructure Audit."""
import pytest

from execution.costs.paper_reconciliation import (
    MicrostructureFillAudit,
    PhaseOInstitutionalScorecard,
    PhaseOReconciliationAuditor,
)


def test_microstructure_fill_audit_execution_drag():
    # Long order with theoretical entry 100, stop 95 (stop distance = 5)
    # Paper fill price = 100.25 -> adverse price delta = +0.25 -> drag R = 0.25 / 5 = 0.05R
    fill = MicrostructureFillAudit(
        fill_id="FILL-001",
        symbol="BTC/USD",
        direction="LONG",
        timestamp_ms=1700000000000,
        theoretical_entry=100.0,
        paper_fill_price=100.25,
        initial_stop_price=95.0,
        target_price=120.0,
        destination_r=4.0,
        observed_spread_bps=1.5,
        realized_slippage_bps=2.0,
        execution_latency_ms=85.0,
    )
    assert fill.stop_distance_pct == 0.05
    assert abs(fill.execution_drag_r - 0.05) < 1e-4


def test_phase_o_scorecard_aggregation():
    auditor = PhaseOReconciliationAuditor()

    # Record 3 fills
    for i in range(3):
        auditor.record_fill(
            MicrostructureFillAudit(
                fill_id=f"FILL-00{i}",
                symbol="BTC/USD",
                direction="LONG",
                timestamp_ms=1700000000000 + i * 1000,
                theoretical_entry=100.0,
                paper_fill_price=100.10 + i * 0.05,
                initial_stop_price=95.0,
                target_price=120.0,
                destination_r=4.0,
                observed_spread_bps=2.0,
                realized_slippage_bps=1.5,
                execution_latency_ms=90.0,
            )
        )

    # Record trade outcomes: +2.0R, -1.0R, +3.0R
    auditor.record_trade_outcome("T-01", 2.0, 48)
    auditor.record_trade_outcome("T-02", -1.0, 12)
    auditor.record_trade_outcome("T-03", 3.0, 60)

    # Record opportunity cycles
    auditor.record_opportunity_cycle(qualified_count=10, opp_count=2, executed=True)
    auditor.record_opportunity_cycle(qualified_count=10, opp_count=1, executed=False, no_trade_reason="NO_TRADE_HEAT_EXCEEDED")

    scorecard = auditor.generate_scorecard(
        portfolio_heat_history=[0.015, 0.020, 0.025],
        single_risk_history=[0.010, 0.010, 0.010],
    )

    # 1. Profitability
    assert scorecard.profitability.total_trades == 3
    assert scorecard.profitability.realized_r == 4.0
    assert abs(scorecard.profitability.expectancy_r - 1.333) < 0.01
    assert abs(scorecard.profitability.win_rate_pct - 66.67) < 0.1
    assert scorecard.profitability.profit_factor == 5.0

    # 2. Microstructure
    assert scorecard.microstructure.avg_spread_bps == 2.0
    assert scorecard.microstructure.avg_latency_ms == 90.0
    assert scorecard.microstructure.fill_rate_pct == 100.0

    # 3. Opportunity Quality
    assert scorecard.opportunity.qualified_instruments == 10
    assert scorecard.opportunity.trades_executed == 1
    assert scorecard.opportunity.no_trade_decisions == 1
    assert scorecard.opportunity.conversion_rate_pct == 50.0

    # 4. Risk Containment
    assert scorecard.risk_containment.max_portfolio_heat_pct == 0.025
    assert scorecard.risk_containment.heat_limit_breaches == 0
    assert scorecard.risk_containment.single_risk_breaches == 0


def test_promotion_gate_rejects_insufficient_sample_size():
    auditor = PhaseOReconciliationAuditor()
    for i in range(15):
        auditor.record_trade_outcome(f"T-{i}", 0.5, 24, symbol="BTC/USD")
        auditor.record_fill(
            MicrostructureFillAudit(
                fill_id=f"F-{i}", symbol="BTC/USD", direction="LONG", timestamp_ms=1700000000000,
                theoretical_entry=100.0, paper_fill_price=100.05, initial_stop_price=95.0,
                target_price=120.0, destination_r=4.0, observed_spread_bps=1.5,
                realized_slippage_bps=1.0, execution_latency_ms=50.0
            )
        )
    scorecard = auditor.generate_scorecard()
    eval_result = auditor.evaluate_promotion_gate(scorecard, observation_days=35.0)

    assert eval_result.is_promotable is False
    assert eval_result.sample_size_passed is False
    assert any("INSUFFICIENT_SAMPLE_SIZE" in r for r in eval_result.rejection_reasons)


def test_promotion_gate_rejects_excessive_concentration():
    auditor = PhaseOReconciliationAuditor()
    # 30 trades: 1 outlier of +10R, and 29 trades of -0.1R -> ExpR is positive but concentrated
    auditor.record_trade_outcome("T-0", 10.0, 24, symbol="BTC/USD", regime="EXPANSION_STABLE")
    auditor.record_fill(
        MicrostructureFillAudit(
            fill_id="F-0", symbol="BTC/USD", direction="LONG", timestamp_ms=1700000000000,
            theoretical_entry=100.0, paper_fill_price=100.05, initial_stop_price=95.0,
            target_price=120.0, destination_r=4.0, observed_spread_bps=1.5,
            realized_slippage_bps=1.0, execution_latency_ms=50.0
        )
    )
    for i in range(1, 30):
        auditor.record_trade_outcome(f"T-{i}", -0.1, 12, symbol="ETH/USD", regime="COMPRESSION_VOLATILE")
        auditor.record_fill(
            MicrostructureFillAudit(
                fill_id=f"F-{i}", symbol="ETH/USD", direction="LONG", timestamp_ms=1700000000000,
                theoretical_entry=100.0, paper_fill_price=100.05, initial_stop_price=95.0,
                target_price=120.0, destination_r=4.0, observed_spread_bps=1.5,
                realized_slippage_bps=1.0, execution_latency_ms=50.0
            )
        )
    scorecard = auditor.generate_scorecard()
    eval_result = auditor.evaluate_promotion_gate(scorecard, observation_days=35.0)

    assert eval_result.is_promotable is False
    assert eval_result.return_concentration_passed is False
    assert any("EXCESSIVE_RETURN_CONCENTRATION" in r for r in eval_result.rejection_reasons)


def test_promotion_gate_accepts_valid_diverse_sample():
    auditor = PhaseOReconciliationAuditor()
    # 32 trades distributed evenly: 16 on BTC, 16 on ETH; 18 wins (+1.2R), 14 losses (-0.8R)
    for i in range(32):
        sym = "BTC/USD" if i % 2 == 0 else "ETH/USD"
        reg = "EXPANSION_STABLE" if i < 16 else "COMPRESSION_VOLATILE"
        r_val = 1.2 if i % 3 != 0 else -0.8
        auditor.record_trade_outcome(f"T-{i}", r_val, 24, symbol=sym, regime=reg)
        auditor.record_fill(
            MicrostructureFillAudit(
                fill_id=f"F-{i}", symbol=sym, direction="LONG", timestamp_ms=1700000000000,
                theoretical_entry=100.0, paper_fill_price=100.08, initial_stop_price=95.0,
                target_price=120.0, destination_r=4.0, observed_spread_bps=1.5,
                realized_slippage_bps=1.0, execution_latency_ms=45.0
            )
        )
    scorecard = auditor.generate_scorecard(
        portfolio_heat_history=[0.015] * 32,
        single_risk_history=[0.010] * 32,
        historical_baseline_exp_r=0.45,
    )
    eval_result = auditor.evaluate_promotion_gate(scorecard, observation_days=35.0)

    assert eval_result.sample_size_passed is True
    assert eval_result.time_exposure_days_passed is True
    assert eval_result.expectancy_floor_passed is True
    assert eval_result.statistical_confidence_passed is True
    assert eval_result.return_concentration_passed is True
    assert eval_result.instrument_diversity_passed is True
    assert eval_result.regime_diversity_passed is True
    assert eval_result.execution_drag_passed is True
    assert eval_result.zero_governance_breaches is True
    assert eval_result.attribution_integrity_passed is True
    assert eval_result.is_promotable is True
    assert eval_result.status_summary == "PROMOTION_GRANTED_TO_MICRO_LIVE"


def test_promotion_gate_rejects_reconciliation_discrepancy():
    auditor = PhaseOReconciliationAuditor()
    for i in range(32):
        sym = "BTC/USD" if i % 2 == 0 else "ETH/USD"
        reg = "EXPANSION_STABLE" if i < 16 else "COMPRESSION_VOLATILE"
        r_val = 1.2 if i % 3 != 0 else -0.8
        auditor.record_trade_outcome(f"T-{i}", r_val, 24, symbol=sym, regime=reg)
        auditor.record_fill(
            MicrostructureFillAudit(
                fill_id=f"F-{i}", symbol=sym, direction="LONG", timestamp_ms=1700000000000,
                theoretical_entry=100.0, paper_fill_price=100.08, initial_stop_price=95.0,
                target_price=120.0, destination_r=4.0, observed_spread_bps=1.5,
                realized_slippage_bps=1.0, execution_latency_ms=45.0
            )
        )
    scorecard = auditor.generate_scorecard(
        portfolio_heat_history=[0.015] * 32,
        single_risk_history=[0.010] * 32,
    )
    # Inject an unreconciled accounting mismatch
    scorecard.attribution.unreconciled_discrepancies = 2
    scorecard.attribution.accounting_integrity_passed = False
    eval_result = auditor.evaluate_promotion_gate(scorecard, observation_days=35.0)

    assert eval_result.is_promotable is False
    assert eval_result.attribution_integrity_passed is False
    assert any("RECONCILIATION_DISCREPANCY" in r for r in eval_result.rejection_reasons)
