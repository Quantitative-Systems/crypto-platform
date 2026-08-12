import pytest
from market_intelligence.trend_engine import TrendEngine, TrendState, TrendHealth
from market_intelligence.primitives import StructureState, TrendDirection, SequenceSwing, RawSwing, SwingType, SequenceLabel
from market_intelligence.phase_engine import PhaseState, MarketPhase

@pytest.fixture
def base_swing():
    return SequenceSwing(
        raw_swing=RawSwing(
            swing_id="SW_1",
            timestamp=1000,
            candle_index=10,
            price=1.0,
            swing_type=SwingType.SWING_LOW,
            confirmation_timestamp=2000,
            confirmation_index=12,
            timeframe="1H"
        ),
        label=SequenceLabel.HL,
        is_strong=True
    )

def test_trend_engine_bullish_strong(base_swing):
    engine = TrendEngine()
    structure = StructureState(
        external_trend=TrendDirection.BULLISH,
        protected_low=base_swing,
        broken_protected_swing_id="SW_OLD_HIGH"
    )
    phase = PhaseState(
        current_phase=MarketPhase.EXPANSION,
        current_trend=TrendDirection.BULLISH
    )
    
    state = engine.evaluate(structure, phase)
    assert state.direction == TrendDirection.BULLISH
    assert state.health == TrendHealth.STRONG
    assert "SW_OLD_HIGH" in state.causal_evidence
    assert "SW_1" in state.causal_evidence

def test_trend_engine_bearish_weakening(base_swing):
    engine = TrendEngine()
    structure = StructureState(
        external_trend=TrendDirection.BEARISH,
        protected_high=base_swing,
    )
    phase = PhaseState(
        current_phase=MarketPhase.PULLBACK,
        current_trend=TrendDirection.BEARISH
    )
    
    state = engine.evaluate(structure, phase)
    assert state.direction == TrendDirection.BEARISH
    assert state.health == TrendHealth.WEAKENING
    assert "SW_1" in state.causal_evidence

def test_trend_engine_ranging():
    engine = TrendEngine()
    structure = StructureState(
        external_trend=TrendDirection.NEUTRAL,
    )
    phase = PhaseState(
        current_phase=MarketPhase.ACCUMULATION,
        current_trend=TrendDirection.NEUTRAL
    )
    
    state = engine.evaluate(structure, phase)
    assert state.direction == TrendDirection.RANGING
    assert state.health == TrendHealth.EXHAUSTED
