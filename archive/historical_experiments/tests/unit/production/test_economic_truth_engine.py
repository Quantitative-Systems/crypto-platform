"""
Tests for Economic Truth & Return Attribution Engine.
"""

from production.economic_truth_engine import (
    EconomicTruthEngine,
    TradeAttributionRecord,
    DegradationDiagnosis,
)


def test_economic_truth_trade_attribution():
    engine = EconomicTruthEngine()

    rec = engine.attribute_trade(
        trade_id="TRD-001",
        alpha_id="FAM-07",
        symbol="SOL/USDT",
        entry_price=100.0,
        exit_price=105.0,
        quantity=10.0,
        is_long=True,
        market_return_pct=2.0
    )

    assert isinstance(rec, TradeAttributionRecord)
    assert rec.gross_pnl_usd == 50.0  # (105 - 100) * 10
    assert rec.net_pnl_usd < rec.gross_pnl_usd  # fees deducted
    assert rec.exchange_fees_usd > 0.0
    assert rec.market_beta_pnl_usd == 20.0  # 1000 * 0.02
    assert rec.pure_alpha_pnl_usd == 30.0   # 50 - 20


def test_degradation_diagnosis():
    engine = EconomicTruthEngine()

    diag = engine.diagnose_performance_degradation(
        alpha_id="FAM-06",
        expected_expectancy_r=0.60,
        observed_expectancy_r=-0.05,
        expected_slippage_bps=3.0,
        observed_slippage_bps=3.2,
        expected_max_dd_r=6.0,
        observed_max_dd_r=15.0
    )

    assert isinstance(diag, DegradationDiagnosis)
    assert diag.is_degraded is True
    assert diag.primary_degradation_cause == "ALPHA_EDGE_DECAY"
