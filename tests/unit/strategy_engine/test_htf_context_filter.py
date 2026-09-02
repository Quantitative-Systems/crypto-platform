"""
Unit tests for hypothesis-context isolation on StrategyCoordinator:
  HYP_A_PULLBACK_RIDING      -> htf_context_filter="PULLBACK"
  HYP_B_CONTINUATION_RIDING  -> htf_context_filter="CONTINUATION"
Verifies that candidates are only spawned in the matching HTF phase context
while existing in-flight candidates keep progressing in subsequent calls.
"""

from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, RawSwing, SequenceSwing, SequenceLabel,
    SwingScope, StructureState, SwingType, MarketPhase,
)
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator


def make_swing(price: float, swing_type: SwingType = SwingType.SWING_LOW, ts: int = 1000) -> SequenceSwing:
    raw = RawSwing(swing_id=f"sw_{ts}", timestamp=ts, price=price, swing_type=swing_type,
                   candle_index=1, confirmation_timestamp=ts, confirmation_index=1, scope=SwingScope.EXTERNAL)
    return SequenceSwing(raw_swing=raw, label=SequenceLabel.HL)


def make_payload(phase: MarketPhase, timestamp: int = 1000) -> MarketStatePayload:
    prot = make_swing(90.0, SwingType.SWING_LOW, ts=timestamp)
    weak = make_swing(150.0, SwingType.SWING_HIGH, ts=timestamp)
    struct = StructureState(
        external_trend=TrendDirection.BULLISH, internal_trend=TrendDirection.BULLISH,
        protected_low=prot, protected_high=None, weak_high=weak, weak_low=None, events=[],
    )
    return MarketStatePayload(
        symbol="BTCUSD", timeframe="1D", timestamp=timestamp, current_price=100.0,
        current_candle=Candle(timestamp=timestamp, open=100.0, high=101.0, low=99.0, close=100.0, volume=100),
        events=[], swings=[], structure_state=struct, liquidity_pools=[], keyzones=[],
        phase_state=phase, trend_state=TrendDirection.BULLISH, valuation_state="EQUILIBRIUM",
        scorecard={"reason_codes": ["DISPLACEMENT_CONFIRMED"]}, metadata={},
    )


def test_pullback_hypothesis_ignores_continuation_phase():
    """HYP_A (PULLBACK filter) must NOT spawn candidates during EXPANSION/CONTINUATION."""
    coordinator = StrategyCoordinator(htf_context_filter="PULLBACK")
    htf = make_payload(phase=MarketPhase.EXPANSION)
    coordinator.evaluate(htf, make_payload(phase=MarketPhase.EXPANSION), make_payload(phase=MarketPhase.PULLBACK))
    assert coordinator.candidate_tracker.get_active_candidates("BTCUSD", "UNIFIED_STRATEGY") == []


def test_continuation_hypothesis_spawns_in_continuation_phase():
    """HYP_B (CONTINUATION filter) MUST spawn candidates during EXPANSION."""
    coordinator = StrategyCoordinator(htf_context_filter="CONTINUATION")
    htf = make_payload(phase=MarketPhase.EXPANSION)
    coordinator.evaluate(htf, make_payload(phase=MarketPhase.EXPANSION), make_payload(phase=MarketPhase.EXPANSION))
    cands = coordinator.candidate_tracker.get_active_candidates("BTCUSD", "UNIFIED_STRATEGY")
    assert len(cands) == 1
    assert cands[0].state == CandidateState.WAIT_MTF_ALIGNMENT


def test_pullback_hypothesis_spawns_in_pullback_phase():
    """HYP_A (PULLBACK filter) MUST spawn candidates during PULLBACK phase."""
    coordinator = StrategyCoordinator(htf_context_filter="PULLBACK")
    htf = make_payload(phase=MarketPhase.PULLBACK)
    coordinator.evaluate(htf, make_payload(phase=MarketPhase.PULLBACK), make_payload(phase=MarketPhase.PULLBACK))
    cands = coordinator.candidate_tracker.get_active_candidates("BTCUSD", "UNIFIED_STRATEGY")
    assert len(cands) == 1
    assert cands[0].htf_context == "PULLBACK"