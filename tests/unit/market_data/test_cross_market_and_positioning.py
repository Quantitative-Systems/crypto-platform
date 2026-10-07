"""Unit tests for Cross-Market and Positioning Engines."""
import numpy as np

from market_intelligence.cross_market.cross_market_engine import (
    CrossMarketSnapshot,
    CrossMarketStateEngine,
)
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningIntelligenceEngine,
    PositioningSnapshot,
    TrappedState,
)


def test_cross_market_engine_correlations_and_divergence():
    engine = CrossMarketStateEngine(correlation_window_bars=25)

    # Simulated returns
    btc_rets = np.array([0.01, -0.02, 0.015, -0.01, 0.03] * 5)
    spx_rets = np.array([0.008, -0.015, 0.012, -0.008, 0.025] * 5)
    dxy_rets = -spx_rets # Strong inverse

    snapshot = engine.evaluate_cross_market(
        timestamp_ms=1_700_000_000_000,
        macro_quotes={
            "dxy": 103.5,
            "dxy_change_24h": -0.4,
            "spx": 5600.0,
            "spx_change_24h": 0.8,
            "vix": 14.5,
            "etf_net_inflow_usd_24h": 450_000_000.0,
        },
        crypto_returns={"BTC": btc_rets},
        macro_returns={"SPX": spx_rets, "DXY": dxy_rets},
    )

    assert snapshot.btc_spx_correlation_30d > 0.80
    assert snapshot.btc_dxy_correlation_30d < -0.80
    assert snapshot.macro_transmission_bias == "BULLISH_RISK_ON"


def test_positioning_trapped_traders():
    pos_engine = PositioningIntelligenceEngine()

    # Case 1: Shorts aggressively fighting a bull trend -> Short Squeeze Prime
    pos_squeeze = pos_engine.evaluate_positioning(
        timestamp_ms=1_700_000_000_000,
        positioning_raw={
            "funding_rate_8h_bps": -15.0, # Shorts heavily paying longs
            "oi_change_pct_24h": 8.5,     # Open interest expanding rapidly
        },
        technical_direction=1, # Long
    )
    assert pos_squeeze.funding_state == FundingState.EXTREME_NEGATIVE
    assert pos_squeeze.trapped_setup == TrappedState.SHORT_SQUEEZE_PRIME
    assert pos_squeeze.edge_alignment_score > 1.0 # Boosts edge score

    # Case 2: Longs over-leveraged in a bull trend -> Long Flush Risk
    pos_flush = pos_engine.evaluate_positioning(
        timestamp_ms=1_700_000_000_000,
        positioning_raw={
            "funding_rate_8h_bps": 38.0,  # Longs paying extreme funding
            "oi_change_pct_24h": 4.0,
        },
        technical_direction=1, # Long
    )
    assert pos_flush.funding_state == FundingState.EXTREME_POSITIVE
    assert pos_flush.trapped_setup == TrappedState.LONG_LIQUIDATION_RISK
    assert pos_flush.edge_alignment_score < 1.0 # Applies sizing haircut
