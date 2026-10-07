"""Unit tests for Market Regime Engine and Narrative Synthesizer."""
import numpy as np

from market_intelligence.events.contracts import EventClockPhase, EventTimeContext
from market_intelligence.narrative.narrative_engine import (
    MarketNarrativeEngine,
    MarketNarrativeState,
)
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes.regime_contracts import (
    CorrelationRegime,
    LiquidityRegime,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)
from market_intelligence.regimes.regime_engine import MarketRegimeEngine
from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructureSnapshot,
    TrendDirection,
    ZonesSnapshot,
)


def _make_mock_state(symbol: str, trend: TrendDirection, phase: MarketPhaseType) -> MarketState:
    return MarketState(
        symbol=symbol,
        timestamp_ms=1_700_000_000_000,
        timeframe="1d",
        close_price=65000.0,
        structure=StructureSnapshot(
            external_trend=trend,
            internal_trend=trend,
            trend_strength=0.8,
            protected_low=60000.0,
        ),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=phase),
        measurements=MeasurementsSnapshot(
            atr=1500.0,
            realized_vol=0.55,
            volume_sma_ratio=1.2,
            adx=28.0,
        ),
    )


def test_market_regime_engine_classification():
    engine = MarketRegimeEngine(vol_lookback_bars=20)
    state = _make_mock_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)

    # Historical closes simulating standard healthy vol
    closes = np.linspace(60000, 65000, 30)

    regime = engine.evaluate_regime(
        current_state=state,
        historical_closes=closes,
        cross_market_data={"macro_correlation": 0.25, "btc_alt_correlation": 0.85},
    )

    assert regime.trend == TrendRegime.TRENDING
    assert regime.liquidity in (LiquidityRegime.NORMAL, LiquidityRegime.ABUNDANT)
    assert regime.volatility in (VolatilityRegime.LOW, VolatilityRegime.NORMAL)
    assert regime.correlation == CorrelationRegime.BTC_LED
    assert regime.is_favorable_for_trend_following is True


def test_phase_vs_regime_decoupling():
    """Verify that Phase (Pullback vs Continuation) does NOT equal Regime."""
    engine = MarketRegimeEngine()
    state_pullback = _make_mock_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.PULLBACK)

    regime = engine.evaluate_regime(current_state=state_pullback)

    # State phase is PULLBACK, but trend regime is still TRENDING because HTF structure is bullish
    assert state_pullback.phase.current_phase == MarketPhaseType.PULLBACK
    assert regime.trend == TrendRegime.TRENDING


def test_narrative_engine_synthesis():
    narrative_engine = MarketNarrativeEngine()
    htf = _make_mock_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    mtf = _make_mock_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.PULLBACK)
    ltf = _make_mock_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)

    regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_000_000,
        volatility=VolatilityRegime.NORMAL,
        liquidity=LiquidityRegime.ABUNDANT,
        correlation=CorrelationRegime.BTC_LED,
        trend=TrendRegime.TRENDING,
        risk=RiskRegime.RISK_ON,
    )

    pos = PositioningSnapshot(
        timestamp_ms=1_700_000_000_000,
        funding_state=FundingState.NEUTRAL,
        trapped_setup=TrappedState.NONE,
    )

    narrative = narrative_engine.synthesize_narrative(
        symbol="BTCUSDT",
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=regime,
        cross_market=None,
        positioning=pos,
        event_context=None,
    )

    assert narrative.symbol == "BTCUSDT"
    assert "BULLISH" in narrative.current_technical_state
    assert narrative.risk_regime == "RISK_ON"
    assert narrative.confidence in ("MEDIUM", "HIGH")
    assert len(narrative.narrative_summary) > 30
