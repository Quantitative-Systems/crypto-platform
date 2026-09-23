"""Unit tests for the Tri-Partite Comparison Engine."""
import os
import numpy as np
import pytest
from crypto_platform.research_engine.comparison_engine import ComparisonEngine, QuantitativeMetrics
from crypto_platform.research_engine.evidence_ledger import EvidenceLedger, EvidenceTier, StrategyEvidenceRecord


def test_evidence_ledger_strict_tier_isolation(tmp_path):
    ledger_path = str(tmp_path / "test_evidence.json")
    ledger = EvidenceLedger(storage_path=ledger_path)

    rec = StrategyEvidenceRecord(
        strategy_id="strat_trend_01",
        tier=EvidenceTier.OUT_OF_SAMPLE,
        period_start="2024-04-01",
        period_end="2026-03-01",
        trade_count=150,
        return_pct=24.5,
        sharpe=1.45,
        sortino=2.10,
        profit_factor=1.65,
        win_rate=0.48,
        expectancy=0.18,
        max_drawdown_pct=11.2,
        turnover=150.0,
        total_fees_bps=5.0,
        slippage_bps=2.0,
    )
    ledger.record_evidence(rec)
    records = ledger.get_records(tier=EvidenceTier.OUT_OF_SAMPLE)
    assert len(records) == 1
    assert records[0].return_pct == 24.5

    # Test invariant: Cannot record live executions while unactivated
    live_rec = StrategyEvidenceRecord(
        strategy_id="strat_live_illegal",
        tier=EvidenceTier.LIVE,
        period_start="2026-01-01",
        period_end="2026-02-01",
        trade_count=5,  # Must fail
        return_pct=1.0,
        sharpe=1.0,
        sortino=1.0,
        profit_factor=1.0,
        win_rate=0.5,
        expectancy=0.1,
        max_drawdown_pct=1.0,
        turnover=5.0,
        total_fees_bps=5.0,
        slippage_bps=2.0,
    )
    with pytest.raises(ValueError, match="Live trading is strictly unactivated"):
        ledger.record_evidence(live_rec)


def test_calculate_metrics_from_returns():
    # 10 synthetic trades: 6 wins of +0.02, 4 losses of -0.01
    returns = [0.02, 0.02, -0.01, 0.02, -0.01, 0.02, 0.02, -0.01, -0.01, 0.02]
    metrics = ComparisonEngine.calculate_metrics_from_returns(returns, duration_days=30.0)

    assert metrics.trade_count == 10
    assert metrics.win_rate == 0.60
    assert metrics.profit_factor == 3.0  # 0.12 / 0.04 = 3.0
    assert metrics.expectancy_r > 0.0
    assert metrics.sharpe > 0.0
    assert metrics.sortino > 0.0


def test_distributional_consistency_detection():
    engine = ComparisonEngine()

    # Identical distributions should be statistically consistent
    r1 = [0.01 * (i % 3 - 1) for i in range(50)]
    r2 = [0.01 * (i % 3 - 1) for i in range(50)]
    p_val, verdict = engine.test_distributional_consistency(r1, r2)
    assert "STATISTICALLY_CONSISTENT" in verdict or p_val >= 0.05

    # Vastly differing distributions should trigger drift detection
    r_normal = list(np.random.normal(0.001, 0.01, 100))
    r_divergent = list(np.random.normal(-0.05, 0.10, 100))
    p_val_div, verdict_div = engine.test_distributional_consistency(r_normal, r_divergent)
    assert "DRIFT" in verdict_div or p_val_div < 0.05


def test_build_comparison_report(tmp_path):
    engine = ComparisonEngine(outdir=str(tmp_path))
    report = engine.build_comparison_report()

    assert "portfolio" in report
    assert "per_strategy" in report
    assert os.path.exists(str(tmp_path / "backtest_vs_oos_vs_paper.json"))
    assert os.path.exists(str(tmp_path / "profitability_validation_report.md"))
