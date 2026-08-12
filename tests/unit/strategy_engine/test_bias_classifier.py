import pytest
from market_intelligence.primitives import MarketStatePayload, TrendDirection
from market_intelligence.phase_engine import MarketPhase
from market_intelligence.structure_builder_engine import StructureState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.classifiers.bias_classifier import BiasClassifier

def create_mock_payload(trend: TrendDirection, phase: MarketPhase) -> MarketStatePayload:
    return MarketStatePayload(
        symbol="BTCUSD",
        timeframe="1D",
        timestamp=1000,
        current_price=100.0,
        current_candle=None,
        events=[],
        swings=[],
        structure_state=StructureState(
            sequence_swings=[],
            external_trend=TrendDirection.NEUTRAL,
            internal_trend=TrendDirection.NEUTRAL,
            protected_high=None,
            protected_low=None,
            weak_high=None,
            weak_low=None,
            dealing_range=None,
            events=[]
        ),
        liquidity_pools=[],
        keyzones=[],
        phase_state=phase,
        trend_state=trend
    )

def test_bias_classifier_bullish_expansion():
    payload = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.PERMIT_LONG

def test_bias_classifier_bullish_pullback():
    payload = create_mock_payload(TrendDirection.BULLISH, MarketPhase.PULLBACK)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.PERMIT_LONG

def test_bias_classifier_bullish_distribution():
    payload = create_mock_payload(TrendDirection.BULLISH, MarketPhase.DISTRIBUTION)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.NO_TRADE

def test_bias_classifier_bearish_expansion():
    payload = create_mock_payload(TrendDirection.BEARISH, MarketPhase.EXPANSION)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.PERMIT_SHORT

def test_bias_classifier_bearish_reversal():
    payload = create_mock_payload(TrendDirection.BEARISH, MarketPhase.REVERSAL)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.NO_TRADE

def test_bias_classifier_ranging():
    payload = create_mock_payload(TrendDirection.RANGING, MarketPhase.ACCUMULATION)
    bias = BiasClassifier.evaluate(payload)
    assert bias == DirectionalPermission.NO_TRADE
