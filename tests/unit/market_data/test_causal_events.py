"""Unit tests for Causal Event Engine and Event Clock."""
from market_intelligence.events.contracts import (
    CausalEvent,
    EventCategory,
    EventClockPhase,
    EventImportance,
    EventSurprise,
    SurpriseDirection,
    TransmissionChain,
)
from market_intelligence.events.event_clock import (
    EventClock,
    MS_IN_HOUR,
    MS_IN_MINUTE,
)
from market_intelligence.events.event_engine import CausalEventEngine


def test_event_surprise_calculations():
    # CPI Higher Than Expected (Hawkish / Bearish Risk)
    surprise = EventSurprise(actual=3.4, expected=3.1, previous=3.0)
    assert abs(surprise.raw_surprise - 0.3) < 1e-6
    assert abs(surprise.period_change - 0.4) < 1e-6
    assert surprise.direction == SurpriseDirection.UPSIDE
    assert abs(surprise.standardized_surprise - (0.3 / 3.1)) < 1e-4

    # PCE Lower Than Expected (Dovish / Bullish Risk)
    surprise_down = EventSurprise(actual=2.6, expected=2.8, previous=2.9)
    assert abs(surprise_down.raw_surprise - (-0.2)) < 1e-6
    assert surprise_down.direction == SurpriseDirection.DOWNSIDE

    # In-Line Print
    surprise_inline = EventSurprise(actual=2.5, expected=2.5)
    assert surprise_inline.raw_surprise == 0.0
    assert surprise_inline.direction == SurpriseDirection.IN_LINE


def test_event_clock_phases_and_gating():
    event_time = 1_700_000_000_000 # Reference epoch ms
    cpi_event = CausalEvent(
        event_id="EVT-CPI-01",
        event_name="US CPI Release",
        category=EventCategory.MACROECONOMIC,
        importance=EventImportance.CRITICAL,
        timestamp_ms=event_time,
        surprise=EventSurprise(actual=3.2, expected=3.1),
        affected_assets=["BTCUSDT", "ETHUSDT"],
    )

    clock = EventClock([cpi_event])

    # T-2h: Compression window, trading allowed
    ctx_t_minus_2h = clock.evaluate_context(event_time - 2 * MS_IN_HOUR)
    assert ctx_t_minus_2h.clock_phase == EventClockPhase.T_MINUS_4H
    assert ctx_t_minus_2h.is_compression_expected is True
    assert ctx_t_minus_2h.is_trading_prohibited is False

    # T-10m: High-risk freeze window, trading PROHIBITED
    ctx_t_minus_10m = clock.evaluate_context(event_time - 10 * MS_IN_MINUTE)
    assert ctx_t_minus_10m.clock_phase == EventClockPhase.T_MINUS_15M
    assert ctx_t_minus_10m.is_trading_prohibited is True

    # At Event (T+5m): Volatility expansion, trading PROHIBITED
    ctx_at_event = clock.evaluate_context(event_time + 5 * MS_IN_MINUTE)
    assert ctx_at_event.clock_phase == EventClockPhase.AT_EVENT
    assert ctx_at_event.is_trading_prohibited is True
    assert ctx_at_event.is_volatility_expansion_expected is True

    # T+30m: Price discovery phase, trading allowed
    ctx_t_plus_30m = clock.evaluate_context(event_time + 30 * MS_IN_MINUTE)
    assert ctx_t_plus_30m.clock_phase == EventClockPhase.T_PLUS_15M
    assert ctx_t_plus_30m.is_trading_prohibited is False

    # T+2h: Structural validation phase
    ctx_t_plus_2h = clock.evaluate_context(event_time + 2 * MS_IN_HOUR)
    assert ctx_t_plus_2h.clock_phase == EventClockPhase.T_PLUS_1H
    assert ctx_t_plus_2h.is_trading_prohibited is False


def test_causal_event_engine_queries():
    engine = CausalEventEngine()
    t1 = 1_000_000
    t2 = 2_000_000

    engine.register_event(
        event_id="E1",
        event_name="FOMC Decision",
        category=EventCategory.MONETARY_POLICY,
        importance=EventImportance.CRITICAL,
        timestamp_ms=t1,
        actual=5.25,
        expected=5.25,
    )
    engine.register_event(
        event_id="E2",
        event_name="BTC ETF Net Inflows",
        category=EventCategory.CRYPTO_NATIVE,
        importance=EventImportance.HIGH,
        timestamp_ms=t2,
        actual=500.0,
        expected=200.0,
        unit="USD_MILLIONS",
    )

    # Causal query at t=1,500,000 must see E1 but NEVER E2 (no lookahead)
    evt = engine.get_latest_event_prior_to(1_500_000)
    assert evt is not None
    assert evt.event_id == "E1"

    # Query at t=2,500,000 sees E2
    evt_latest = engine.get_latest_event_prior_to(2_500_000)
    assert evt_latest is not None
    assert evt_latest.event_id == "E2"

    # Category filter
    evt_macro = engine.get_latest_event_prior_to(2_500_000, category=EventCategory.MONETARY_POLICY)
    assert evt_macro is not None
    assert evt_macro.event_id == "E1"
