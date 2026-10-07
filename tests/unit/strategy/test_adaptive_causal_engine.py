"""Unit tests for the integrated Adaptive Causal Engine."""
from execution.decision_ledger import DecisionType
from market_intelligence.events.contracts import (
    CausalEvent,
    EventCategory,
    EventImportance,
    EventSurprise,
)
from market_intelligence.events.event_engine import CausalEventEngine
from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from strategy.adaptive.adaptive_causal_engine import AdaptiveCausalEngine


def _make_state(
    symbol: str,
    tf: str,
    trend: TrendDirection,
    phase: MarketPhaseType,
    close: float,
    ts_ms: int,
) -> MarketState:
    return MarketState(
        symbol=symbol,
        timestamp_ms=ts_ms,
        timeframe=tf,
        close_price=close,
        structure=StructureSnapshot(
            external_trend=trend,
            internal_trend=trend,
            trend_strength=0.8,
            protected_low=close * 0.95,
            protected_high=close * 1.05,
            last_major_high=SwingPoint(timestamp_ms=ts_ms, price=close * 1.08, is_high=True),
            last_minor_high=SwingPoint(timestamp_ms=ts_ms, price=close * 1.02, is_high=True),
            last_minor_low=SwingPoint(timestamp_ms=ts_ms, price=close * 0.98, is_high=False),
        ),
        zones=ZonesSnapshot(
            premium_discount_zone="DISCOUNT",
            equilibrium_price=close,
        ),
        phase=PhaseSnapshot(current_phase=phase),
        measurements=MeasurementsSnapshot(
            atr=close * 0.015,
            volume_sma_ratio=1.2,
            adx=26.0,
        ),
    )


def test_adaptive_causal_engine_event_blocking():
    event_engine = CausalEventEngine()
    ts_ref = 1_700_000_000_000

    # Schedule critical CPI event 10 minutes into the future
    event_engine.register_event(
        event_id="EVT-CPI-TEST",
        event_name="CPI Release",
        category=EventCategory.MACROECONOMIC,
        importance=EventImportance.CRITICAL,
        timestamp_ms=ts_ref + 10 * 60 * 1000, # 10 mins away
        actual=3.1,
    )

    causal_engine = AdaptiveCausalEngine(
        timeframe_set_id="SET_2",
        htf_label="1w",
        mtf_label="1d",
        ltf_label="4h",
        event_engine=event_engine,
    )

    htf = _make_state("BTCUSDT", "1w", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION, 65000, ts_ref)
    mtf = _make_state("BTCUSDT", "1d", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION, 65000, ts_ref)
    ltf = _make_state("BTCUSDT", "4h", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION, 65000, ts_ref)

    signal, record, narrative = causal_engine.evaluate_causal_decision(
        bar_idx=50,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        symbol="BTCUSDT",
    )

    # Even if technical structure is bullish, event freeze MUST block execution
    assert signal is None
    assert record.decision == DecisionType.NO_TRADE
    assert any("Event Clock Gating" in b for b in record.blockers)
    assert narrative.confidence == "LOW"
