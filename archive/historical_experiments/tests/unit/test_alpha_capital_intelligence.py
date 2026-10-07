"""
Unit tests for Alpha & Capital Intelligence Layer.
"""

import pytest
from capital_intelligence.alpha_capital_intelligence import (
    NetEdgeEngine,
    AlphaConfidenceEngine,
    ConfidenceBand,
    AlphaCapacityEngine,
    AlphaSelectionEngine,
    FactorAttributionEngine,
    AlphaHealthEngine,
    AlphaHealthStatus,
)


def test_net_edge_calculation_and_no_trade_gate():
    # 1. Viable trade with strong alpha (+0.25R)
    res_viable = NetEdgeEngine.calculate_net_edge(
        symbol="SOLUSDT",
        direction="LONG",
        gross_alpha_r=0.25,
        stop_distance_pct=3.5,  # 3.5% stop
        order_notional_usd=1000.0,
    )
    assert res_viable.is_economically_viable is True
    assert res_viable.verdict == "TRADE"
    assert res_viable.expected_net_edge_r > 0.05
    assert res_viable.fee_drag_r > 0

    # 2. Sub-threshold weak alpha (+0.05R gross alpha -> negative net edge)
    res_weak = NetEdgeEngine.calculate_net_edge(
        symbol="SOLUSDT",
        direction="LONG",
        gross_alpha_r=0.05,
        stop_distance_pct=3.5,
        order_notional_usd=1000.0,
    )
    assert res_weak.is_economically_viable is False
    assert res_weak.verdict == "NO_TRADE"
    assert "BELOW ECONOMIC VIABILITY" in res_weak.rationale


def test_alpha_confidence_metrics():
    # High sample size (N=500), consistent positive distribution
    trades_high_n = [0.25] * 500
    conf_high = AlphaConfidenceEngine.evaluate_confidence("STRAT-HIGH", trades_high_n)
    assert conf_high.confidence_band == ConfidenceBand.HIGH
    assert conf_high.confidence_score >= 0.70
    assert conf_high.confidence_interval_95[0] > 0.08

    # Low sample size (N=25)
    trades_low_n = [0.25] * 25
    conf_low = AlphaConfidenceEngine.evaluate_confidence("STRAT-LOW", trades_low_n)
    assert conf_low.confidence_band in (ConfidenceBand.LOW, ConfidenceBand.UNRELIABLE)
    assert conf_low.confidence_score < 0.60


def test_alpha_capacity_curve():
    curve = AlphaCapacityEngine.evaluate_capacity_curve(
        strategy_id="STRAT-CAP",
        symbol="BTCUSDT",
        baseline_net_expectancy_r=0.22,
        stop_distance_pct=4.2,
    )
    assert len(curve) == len(AlphaCapacityEngine.CAPITAL_TIERS)
    # Impact at $10 should be near 0
    assert curve[0].estimated_impact_bps < 0.1
    assert curve[0].is_capacity_exceeded is False
    # Impact at $10,000,000 should be larger
    assert curve[-1].estimated_impact_bps > curve[0].estimated_impact_bps


def test_factor_attribution_decomposition():
    att = FactorAttributionEngine.attribute_returns(
        total_realized_r=100.0,
        strategy_family="FAM-07-MTFCONT",
        market_regime_trend_score=1.0,
        market_volatility_expansion_score=0.8,
    )
    assert att.trend_beta_pnl_r > 40.0
    assert att.primary_alpha_driver == "Trend Beta"


def test_alpha_health_clock_decay():
    # Nominal health
    health_norm, status_norm, _ = AlphaHealthEngine.compute_health_index(
        strategy_id="STRAT-HEALTH",
        historical_expectancy_r=0.25,
        recent_expectancy_r=0.24,
        current_drawdown_r=5.0,
        historical_max_dd_r=15.0,
        recent_win_rate=44.0,
        historical_win_rate=45.0,
        sample_size_recent=30,
    )
    assert status_norm == AlphaHealthStatus.NORMAL
    assert health_norm >= 85.0

    # Catastrophic edge decay (Expectancy negative, large DD)
    health_decay, status_decay, _ = AlphaHealthEngine.compute_health_index(
        strategy_id="STRAT-HEALTH",
        historical_expectancy_r=0.25,
        recent_expectancy_r=-0.05,
        current_drawdown_r=22.0,  # > 15R historical
        historical_max_dd_r=15.0,
        recent_win_rate=28.0,
        historical_win_rate=45.0,
        sample_size_recent=30,
    )
    assert status_decay in (AlphaHealthStatus.QUARANTINE, AlphaHealthStatus.REDUCE, AlphaHealthStatus.RETIRE)
    assert health_decay < 50.0
