"""
Unit tests for QCP OpportunityDetector across the full crypto opportunity surface.
"""

import pytest
from market_intelligence.continuous_regime_engine import (
    RegimeState,
    TrendState,
    VolatilityState,
    LiquidityState,
    FundingState,
    CorrelationState
)
from market_intelligence.opportunity_detector import OpportunityDetector, OpportunityType
from market_data.universal_data_fabric import OrderBookSnapshot, OrderBookLevel


@pytest.fixture
def dummy_regimes():
    rs_sol = RegimeState(
        symbol="SOL/USDT",
        timestamp_utc="2026-09-16T12:00:00Z",
        trend=TrendState.BULL_MOMENTUM,
        trend_strength_score=0.92,
        volatility=VolatilityState.LOW_VOL_SQUEEZE,
        volatility_percentile=15.0,
        liquidity=LiquidityState.NORMAL_DEPTH,
        liquidity_depth_ratio=1.5,
        funding=FundingState.EXTREME_POSITIVE_FUNDING,
        annualized_funding_pct=65.0,
        correlation=CorrelationState.DISPERSED_MARKET,
        systemic_coupling_score=0.15
    )
    rs_btc = RegimeState(
        symbol="BTC/USDT",
        timestamp_utc="2026-09-16T12:00:00Z",
        trend=TrendState.SIDEWAYS_CHOP,
        trend_strength_score=0.20,
        volatility=VolatilityState.NORMAL_VOL,
        volatility_percentile=50.0,
        liquidity=LiquidityState.NORMAL_DEPTH,
        liquidity_depth_ratio=1.0,
        funding=FundingState.NEUTRAL_CARRY,
        annualized_funding_pct=8.0,
        correlation=CorrelationState.COUPLED_SYSTEMIC_SHOCK,
        systemic_coupling_score=0.85
    )
    return [rs_sol, rs_btc]


def test_detect_regime_opportunities(dummy_regimes):
    detector = OpportunityDetector()
    opps = detector.detect_opportunities(dummy_regimes)

    # From SOL: Should detect CARRY, VOLATILITY_SQUEEZE, TREND_MOMENTUM, and DISPERSION_DIVERGENCE
    types = {o.opportunity_type for o in opps}
    assert OpportunityType.FUNDING_ANOMALY in types
    assert OpportunityType.VOLATILITY_SQUEEZE in types
    assert OpportunityType.TREND_MOMENTUM in types
    assert OpportunityType.DISPERSION_DIVERGENCE in types

    carry_opp = next(o for o in opps if o.opportunity_type == OpportunityType.FUNDING_ANOMALY)
    assert carry_opp.symbol == "SOL/USDT"
    assert carry_opp.magnitude_score > 0.5
    assert len(carry_opp.required_data_tokens) >= 2


def test_detect_microstructure_and_flow_opportunities(dummy_regimes):
    detector = OpportunityDetector()

    # Create mock book snapshot with depth imbalance
    book = OrderBookSnapshot(
        symbol="SOL/USDT",
        venue="BINANCE",
        timestamp_ms=1700000000000,
        bids=[OrderBookLevel(price=150.0, size=100.0)],
        asks=[OrderBookLevel(price=150.1, size=10.0)]
    )

    opps = detector.detect_opportunities(
        regime_states=dummy_regimes,
        order_book_snapshots={"SOL/USDT": book},
        cross_venue_spreads_bps={"SOL/USDT": 18.0},
        liquidation_volumes_usd={"SOL/USDT": 1_200_000.0}
    )

    types = {o.opportunity_type for o in opps}
    assert OpportunityType.LIQUIDITY_IMBALANCE in types
    assert OpportunityType.CROSS_EXCHANGE_DISLOCATION in types
    assert OpportunityType.LIQUIDATION_CASCADE in types
